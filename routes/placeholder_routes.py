from flask import Blueprint
placeholder_routes = Blueprint("placeholder_routes", __name__)

from flask import send_file, current_app, Response
import io
import os

try:  # Pillow pode não estar instalado em todos os ambientes
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover - caminho de fallback
    Image = ImageDraw = ImageFont = None



@placeholder_routes.route('/api/placeholder/<int:width>/<int:height>')
def placeholder_image(width, height):
    try:
        if Image is None:
            return Response(
                f"Placeholder {width}x{height}",
                mimetype="text/plain",
                status=200,
            )

        # Crie uma imagem placeholder
        img = Image.new('RGB', (width, height), color=(200, 200, 200))
        d = ImageDraw.Draw(img)
        

        # Tente carregar a fonte Arial ou use a fonte padrão se não estiver disponível
        try:
            font = ImageFont.truetype("arial.ttf", 30)
        except IOError:
            # Fallback para uma fonte que provavelmente existe no sistema
            font = None
            # Tenta encontrar o diretório de fontes em múltiplos locais
            font_dirs = [
                os.path.join(current_app.root_path, "fonts"),
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "fonts"),
                "fonts",
                os.path.join(os.getcwd(), "fonts")
            ]
            
            for font_dir in font_dirs:
                font_path = os.path.join(font_dir, "DejaVuSans.ttf")
                if os.path.exists(font_path):
                    try:
                        font = ImageFont.truetype(font_path, 30)
                        break
                    except IOError:
                        continue
            
            if font is None:
                # Se nenhuma fonte específica estiver disponível, use a fonte padrão
                font = ImageFont.load_default()

        
        # Desenhe o texto na imagem
        text = f"{width} x {height}"
        text_width, text_height = d.textsize(text, font=font) if hasattr(d, 'textsize') else (100, 30)
        d.text(((width-text_width)//2, (height-text_height)//2), text, fill=(80, 80, 80), font=font)
        
        # Salve a imagem em memória e a envie como resposta
        img_io = io.BytesIO()
        img.save(img_io, 'JPEG', quality=70)
        img_io.seek(0)
        return send_file(img_io, mimetype='image/jpeg')
    except Exception as e:
        # Em caso de erro, retorne uma imagem padrão muito simples
        current_app.logger.error(f"Erro ao gerar imagem placeholder: {str(e)}")
        img = Image.new('RGB', (width, height), color=(200, 200, 200))
        img_io = io.BytesIO()
        img.save(img_io, 'JPEG', quality=70)
        img_io.seek(0)
        return send_file(img_io, mimetype='image/jpeg')

