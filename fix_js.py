import re

path = 'c:/Users/andre/Documents/system/templates/auth/cadastro_participante.html'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# Replace occurrences of onclick="openSpeakerModal('{{ ... }}', '{{ ... }}', '{{ ... }}')"
pattern = r"onclick=\"openSpeakerModal\('\{\{ (.*?) \}\}', '\{\{ (.*?) \}\}', '\{\{ (.*?) \}\}'\)\""
replacement = r'onclick="openSpeakerModal({{ \1 |tojson|forceescape }}, {{ \2 |tojson|forceescape }}, {{ \3 |tojson|forceescape }})"'

new_text, count = re.subn(pattern, replacement, text)
print(f"Substituições de openSpeakerModal: {count}")

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_text)
