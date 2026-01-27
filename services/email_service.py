"""Unified email service supporting Mailjet API and Flask-Mail SMTP fallback."""

from __future__ import annotations

import base64
import logging
import mimetypes
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

from flask import current_app, has_app_context, render_template
from flask_mail import Message

from extensions import mail

logger = logging.getLogger(__name__)

RecipientInput = Union[str, Tuple[str, str], Dict[str, Any]]
AttachmentInput = Union[str, Tuple[str, bytes], Tuple[str, bytes, str], Dict[str, Any]]


@dataclass(frozen=True)
class Recipient:
    email: str
    name: Optional[str] = None

    def as_mailjet(self) -> Dict[str, str]:
        data = {"Email": self.email}
        if self.name:
            data["Name"] = self.name
        return data

    def as_address(self) -> str:
        return f"{self.name} <{self.email}>" if self.name else self.email


@dataclass(frozen=True)
class Attachment:
    filename: str
    content: bytes
    content_type: str = "application/octet-stream"

    def as_mailjet(self) -> Dict[str, str]:
        return {
            "ContentType": self.content_type,
            "Filename": self.filename,
            "Base64Content": base64.b64encode(self.content).decode("ascii"),
        }


class EmailService:
    """Centralised email sending service with provider fallbacks."""

    def __init__(self) -> None:
        self._mailjet_client = None
        self._mailjet_auth: Optional[Tuple[str, str]] = None

    # ------------------------------------------------------------------
    #  Public API
    # ------------------------------------------------------------------
    
    def _validate_template(self, template_path: str) -> bool:
        """Valida se um template existe."""
        try:
            from flask import render_template_string
            import os
            
            # Verificar se o arquivo existe
            full_path = os.path.join('templates', template_path)
            if not os.path.exists(full_path):
                return False
            
            # Tentar renderizar o template para validar sintaxe
            with open(full_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            # Renderizar com contexto vazio para validar sintaxe
            render_template_string(template_content)
            return True
            
        except Exception as e:
            logger.error(f"Erro ao validar template {template_path}: {e}")
            return False

    def enviar_certificado_revisor(self, certificado) -> bool:
        """Envia certificado de revisor por email."""
        try:
            logger.info(f"Iniciando envio de certificado para revisor: {certificado.revisor.email}")
            
            # Preparar dados do email
            assunto = f"Certificado de Revisor - {certificado.cliente.nome}"
            
            # Preparar anexo
            anexos = []
            if certificado.arquivo_path and os.path.exists(certificado.arquivo_path):
                with open(certificado.arquivo_path, 'rb') as f:
                    conteudo = f.read()
                anexos.append((
                    f"certificado_revisor_{certificado.revisor.nome.replace(' ', '_')}.pdf",
                    conteudo,
                    'application/pdf'
                ))
                logger.info(f"Anexo preparado: {certificado.arquivo_path}")
            else:
                logger.warning(f"Arquivo de certificado não encontrado: {certificado.arquivo_path}")
            
            # Preparar contexto do template
            contexto = {
                'revisor_nome': certificado.revisor.nome,
                'cliente_nome': certificado.cliente.nome,
                'evento_nome': certificado.evento.nome if certificado.evento else '',
                'trabalhos_revisados': certificado.trabalhos_revisados,
                'data_liberacao': certificado.data_liberacao.strftime('%d/%m/%Y') if certificado.data_liberacao else '',
                'titulo_certificado': certificado.titulo,
            }
            
            # Validar template
            template_path = 'email/certificado_revisor.html'
            if not self._validate_template(template_path):
                logger.error(f"Template não encontrado: {template_path}")
                return False
            
            # Enviar email
            resultado = self.send_email(
                subject=assunto,
                to=(certificado.revisor.email, certificado.revisor.nome),
                template=template_path,
                template_context=contexto,
                attachments=anexos
            )
            
            success = resultado.get('success', False)
            if success:
                logger.info(f"Certificado enviado com sucesso para: {certificado.revisor.email}")
            else:
                logger.error(f"Falha ao enviar certificado para: {certificado.revisor.email}")
            
            return success
            
        except Exception as e:
            logger.error(f"Erro ao enviar certificado de revisor: {e}", exc_info=True)
            return False

    def send_email(
        self,
        *,
        subject: str,
        to: Union[RecipientInput, Sequence[RecipientInput]],
        text: Optional[str] = None,
        html: Optional[str] = None,
        template: Optional[str] = None,
        template_context: Optional[Dict[str, Any]] = None,
        sender: Optional[RecipientInput] = None,
        cc: Optional[Sequence[RecipientInput]] = None,
        bcc: Optional[Sequence[RecipientInput]] = None,
        reply_to: Optional[RecipientInput] = None,
        attachments: Optional[Sequence[AttachmentInput]] = None,
    ) -> Dict[str, Any]:
        """Send an email using Mailjet or SMTP depending on configuration."""
        
        try:
            logger.info(f"Iniciando envio de email - Assunto: {subject}")
            
            recipients = self._normalise_recipients(to)
            if not recipients:
                logger.error("Email requer pelo menos um destinatário")
                raise ValueError("Email requires at least one recipient")

            sender_recipient = self._resolve_sender(sender)
            if not sender_recipient:
                logger.error("MAIL_DEFAULT_SENDER não configurado e nenhum remetente fornecido")
                raise RuntimeError(
                    "MAIL_DEFAULT_SENDER is not configured and no sender was provided."
                )

            # Validar template se fornecido
            if template and not self._validate_template(template):
                logger.error(f"Template inválido: {template}")
                raise ValueError(f"Template não encontrado ou inválido: {template}")

            html = html or self._render_template(template, template_context)
            att_objs = self._normalise_attachments(attachments)
            cc_recipients = self._normalise_recipients(cc) if cc else []
            bcc_recipients = self._normalise_recipients(bcc) if bcc else []
            reply_to_recipient = self._normalise_single_recipient(reply_to)

            logger.info(f"Destinatários: {[r.email for r in recipients]}")
            logger.info(f"Remetente: {sender_recipient.email}")
            logger.info(f"Anexos: {len(att_objs)}")

            client = self._get_mailjet_client()
            if client:
                logger.info("Usando Mailjet para envio")
                result = self._send_mailjet(
                    client=client,
                    sender=sender_recipient,
                    to=recipients,
                    subject=subject,
                    text=text,
                    html=html,
                    attachments=att_objs,
                    cc=cc_recipients,
                    bcc=bcc_recipients,
                    reply_to=reply_to_recipient,
                )
                logger.info(f"Email enviado via Mailjet com sucesso")
                return result

            if not self._can_use_smtp():
                logger.error("Nenhum provedor de email configurado")
                raise RuntimeError(
                    "No email provider configured: set Mailjet credentials or SMTP settings."
                )

            logger.info("Usando SMTP para envio")
            result = self._send_smtp(
                sender=sender_recipient,
                to=recipients,
                subject=subject,
                text=text,
                html=html,
                attachments=att_objs,
                cc=cc_recipients,
                bcc=bcc_recipients,
                reply_to=reply_to_recipient,
            )
            logger.info(f"Email enviado via SMTP com sucesso")
            return result
            
        except Exception as e:
            logger.error(f"Erro ao enviar email: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def enviar_email_unificado(
        self,
        destinatario: str,
        nome_participante: str,
        nome_oficina: str,
        assunto: str,
        corpo_texto: str,
        anexo_path: Optional[str] = None,
        corpo_html: Optional[str] = None,
        template_path: Optional[str] = None,
        template_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Função unificada que substitui o sistema legacy de envio de emails.
        Compatível com a interface antiga mas usando o novo EmailService.
        """
        try:
            logger.info(f"Enviando email unificado para: {destinatario}")
            
            # Preparar HTML
            if corpo_html is None:
                if template_path:
                    # Validar template
                    if not self._validate_template(template_path):
                        logger.error(f"Template não encontrado: {template_path}")
                        return {"success": False, "error": f"Template não encontrado: {template_path}"}
                    
                    corpo_html = self._render_template(template_path, template_context or {})
                else:
                    # HTML padrão para compatibilidade
                    corpo_html = f"""
                    <html>
                    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                        <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                            <h2 style="color: #2C3E50; text-align: center;">Confirmação de Inscrição</h2>
                            <p>Olá, <b>{nome_participante}</b>!</p>
                            <p>Você se inscreveu com sucesso na oficina <b>{nome_oficina}</b>.</p>
                            <p>Aguardamos você no evento!</p>

                            <div style="padding: 15px; background-color: #f4f4f4; border-left: 5px solid #3498db;">
                                <p><b>Detalhes da Oficina:</b></p>
                                <p><b>Nome:</b> {nome_oficina}</p>
                            </div>

                            <p>Caso tenha dúvidas, entre em contato conosco.</p>
                            <p style="text-align: center;">
                                <b>Equipe Organizadora</b>
                            </p>
                        </div>
                    </body>
                    </html>
                    """
            
            # Preparar anexos
            attachments = [anexo_path] if anexo_path else None
            
            # Enviar email
            resultado = self.send_email(
                to=destinatario,
                subject=assunto,
                text=corpo_texto,
                html=corpo_html,
                attachments=attachments,
            )
            
            if resultado.get('success', False):
                logger.info(f"✅ E-mail enviado com sucesso para {destinatario}")
                return {"success": True, "message": "Email enviado com sucesso"}
            else:
                logger.error(f"❌ Falha ao enviar email para {destinatario}")
                return {"success": False, "error": resultado.get('error', 'Erro desconhecido')}
                
        except Exception as e:
            logger.error(f"Erro ao enviar email unificado: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    #  Provider helpers
    # ------------------------------------------------------------------

    def _get_mailjet_client(self):
        api_key, secret = self._mailjet_credentials()
        if not api_key or not secret:
            return None
        if self._mailjet_client and self._mailjet_auth == (api_key, secret):
            return self._mailjet_client
        try:
            from mailjet_rest import Client  # Imported lazily when available
        except ImportError:  # pragma: no cover
            logger.warning("mailjet_rest not installed; falling back to SMTP")
            return None
        self._mailjet_client = Client(auth=(api_key, secret), version="v3.1")
        self._mailjet_auth = (api_key, secret)
        return self._mailjet_client

    def _mailjet_credentials(self) -> Tuple[Optional[str], Optional[str]]:
        config = self._get_config()
        return (
            config.get("MAILJET_API_KEY")
            or os.getenv("MAILJET_API_KEY")
            or config.get("MAIL_USERNAME")
            or os.getenv("MAIL_USERNAME"),
            config.get("MAILJET_SECRET_KEY")
            or os.getenv("MAILJET_SECRET_KEY")
            or config.get("MAIL_PASSWORD")
            or os.getenv("MAIL_PASSWORD"),
        )

    def _can_use_smtp(self) -> bool:
        config = self._get_config()
        return bool(config.get("MAIL_SERVER"))

    def _get_config(self) -> Dict[str, Any]:
        if has_app_context():
            return current_app.config
        return {}

    # ------------------------------------------------------------------
    #  Normalisation helpers
    # ------------------------------------------------------------------

    def _normalise_recipients(
        self, recipients: Optional[Union[RecipientInput, Sequence[RecipientInput]]]
    ) -> List[Recipient]:
        if not recipients:
            return []
        if isinstance(recipients, (str, bytes)) or not isinstance(recipients, Iterable):
            recipients = [recipients]  # type: ignore[assignment]

        normalised: List[Recipient] = []
        for entry in recipients:  # type: ignore[assignment]
            recipient = self._normalise_single_recipient(entry)
            if recipient:
                normalised.append(recipient)
        return normalised

    def _normalise_single_recipient(
        self, entry: Optional[RecipientInput]
    ) -> Optional[Recipient]:
        if not entry:
            return None
        if isinstance(entry, Recipient):
            return entry
        if isinstance(entry, dict):
            email = entry.get("email") or entry.get("Email")
            name = entry.get("name") or entry.get("Name")
        elif isinstance(entry, (list, tuple)):
            if not entry:
                return None
            email = entry[0]
            name = entry[1] if len(entry) > 1 else None
        else:
            email = str(entry)
            name = None
        if not email:
            return None
        email = str(email).strip()
        if not email:
            return None
        name = str(name).strip() if name else None
        return Recipient(email=email, name=name or None)

    def _resolve_sender(self, sender: Optional[RecipientInput]) -> Optional[Recipient]:
        if sender:
            resolved = self._normalise_single_recipient(sender)
            if resolved:
                return resolved
        config = self._get_config()
        default_sender = config.get("MAIL_DEFAULT_SENDER") or os.getenv(
            "MAIL_DEFAULT_SENDER"
        )
        if isinstance(default_sender, (list, tuple)):
            return self._normalise_single_recipient(tuple(default_sender))
        if isinstance(default_sender, dict):
            return self._normalise_single_recipient(default_sender)
        if default_sender:
            return Recipient(email=str(default_sender))
        return None

    def _render_template(
        self,
        template: Optional[str],
        context: Optional[Dict[str, Any]],
    ) -> Optional[str]:
        if not template:
            return None
        context = context or {}
        return render_template(template, **context)

    def _normalise_attachments(
        self, attachments: Optional[Sequence[AttachmentInput]]
    ) -> List[Attachment]:
        if not attachments:
            return []
        results: List[Attachment] = []
        for item in attachments:
            if not item:
                continue
            if isinstance(item, Attachment):
                results.append(item)
                continue
            if isinstance(item, str):
                path = Path(item)
                try:
                    content = path.read_bytes()
                except FileNotFoundError as exc:
                    logger.error("Attachment %s not found: %s", path, exc)
                    continue
                content_type = (
                    mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                )
                results.append(
                    Attachment(
                        filename=path.name,
                        content=content,
                        content_type=content_type,
                    )
                )
                continue
            if isinstance(item, dict):
                filename = item.get("filename") or item.get("name")
                content = item.get("content") or item.get("data")
                content_type = (
                    item.get("content_type")
                    or item.get("mimetype")
                    or (mimetypes.guess_type(filename or "")[0] if filename else None)
                    or "application/octet-stream"
                )
                if isinstance(content, str):
                    content = content.encode("utf-8")
                if filename and content:
                    results.append(
                        Attachment(
                            filename=str(filename),
                            content=content,
                            content_type=str(content_type),
                        )
                    )
                continue
            if isinstance(item, (list, tuple)):
                if len(item) == 3:
                    filename, content, content_type = item
                elif len(item) == 2:
                    filename, content = item
                    content_type = (
                        mimetypes.guess_type(str(filename))[0] or "application/octet-stream"
                    )
                else:
                    continue
                if isinstance(content, str):
                    content = content.encode("utf-8")
                results.append(
                    Attachment(
                        filename=str(filename),
                        content=content,
                        content_type=str(content_type),
                    )
                )
        return results

    # ------------------------------------------------------------------
    #  Provider implementations
    # ------------------------------------------------------------------

    def _send_mailjet(
        self,
        *,
        client,
        sender: Recipient,
        to: List[Recipient],
        subject: str,
        text: Optional[str],
        html: Optional[str],
        attachments: List[Attachment],
        cc: List[Recipient],
        bcc: List[Recipient],
        reply_to: Optional[Recipient],
    ) -> Dict[str, Any]:
        message: Dict[str, Any] = {
            "From": sender.as_mailjet(),
            "To": [recipient.as_mailjet() for recipient in to],
            "Subject": subject,
        }
        if text:
            message["TextPart"] = text
        if html:
            message["HTMLPart"] = html
        if cc:
            message["Cc"] = [recipient.as_mailjet() for recipient in cc]
        if bcc:
            message["Bcc"] = [recipient.as_mailjet() for recipient in bcc]
        if reply_to:
            message["ReplyTo"] = reply_to.as_mailjet()
        if attachments:
            message["Attachments"] = [att.as_mailjet() for att in attachments]

        response = client.send.create(data={"Messages": [message]})
        logger.info(
            "Email sent via Mailjet to %s (subject=%s)",
            ", ".join(rec.email for rec in to),
            subject,
        )
        payload = response.json() if hasattr(response, "json") else response
        return {"provider": "mailjet", "response": payload}

    def _send_smtp(
        self,
        *,
        sender: Recipient,
        to: List[Recipient],
        subject: str,
        text: Optional[str],
        html: Optional[str],
        attachments: List[Attachment],
        cc: List[Recipient],
        bcc: List[Recipient],
        reply_to: Optional[Recipient],
    ) -> Dict[str, Any]:
        message = Message(
            subject=subject,
            recipients=[recipient.email for recipient in to],
            cc=[recipient.email for recipient in cc] or None,
            bcc=[recipient.email for recipient in bcc] or None,
            sender=sender.as_address(),
            reply_to=reply_to.as_address() if reply_to else None,
        )
        if text:
            message.body = text
        if html:
            message.html = html
        for attachment in attachments:
            message.attach(attachment.filename, attachment.content_type, attachment.content)

        mail.send(message)
        logger.info(
            "Email sent via SMTP to %s (subject=%s)",
            ", ".join(rec.email for rec in to),
            subject,
        )
        return {"provider": "smtp", "message_id": getattr(message, "message_id", None)}


email_service = EmailService()


def send_email(
    *, subject: str, to: Union[RecipientInput, Sequence[RecipientInput]], **kwargs
) -> Dict[str, Any]:
    """Convenience wrapper mirroring :meth:`EmailService.send_email`."""
    return email_service.send_email(subject=subject, to=to, **kwargs)
