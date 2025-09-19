@echo off
REM Script para agendar verificações automáticas de alertas de compras no Windows
REM Execute este script como administrador para configurar as tarefas agendadas

echo Configurando verificações automáticas de alertas de compras...

REM Verificação diária às 08:00
schtasks /create /tn "Alertas Compras - Diário" /tr "python %~dp0verificar_alertas_compras.py" /sc daily /st 08:00 /f

REM Verificação semanal às segundas-feiras às 09:00
schtasks /create /tn "Alertas Compras - Semanal" /tr "python %~dp0verificar_alertas_compras.py" /sc weekly /d MON /st 09:00 /f

echo.
echo Tarefas agendadas criadas com sucesso!
echo.
echo Para verificar as tarefas criadas, execute:
echo schtasks /query /tn "Alertas Compras*"
echo.
echo Para remover as tarefas, execute:
echo schtasks /delete /tn "Alertas Compras - Diário" /f
echo schtasks /delete /tn "Alertas Compras - Semanal" /f

pause