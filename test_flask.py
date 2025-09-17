# -*- coding: utf-8 -*-
from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return '<h1>Flask esta funcionando!</h1>'

@app.route('/editor')
def editor():
    try:
        return render_template('editor/canva_editor.html')
    except Exception as e:
        return '<h1>Erro ao carregar editor: ' + str(e) + '</h1>'

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)