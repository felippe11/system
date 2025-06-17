from flask import Blueprint, render_template, abort

static_page_routes = Blueprint('static_page_routes', __name__, template_folder="../templates/pages")

# Map slugs to page titles
PAGES = {
    'empresa': 'Empresa',
    'sobre-nos': 'Sobre nós',
    'nosso-time': 'Nosso time',
    'carreiras': 'Carreiras',
    'blog': 'Blog',
    'eventos': 'Eventos',
    'conferencias': 'Conferências',
    'workshops': 'Workshops',
    'formacoes': 'Formações',
    'seminarios': 'Seminários',
    'suporte': 'Suporte',
    'faq': 'FAQ',
    'central-de-ajuda': 'Central de ajuda',
    'contato': 'Contato',
    'tutoriais': 'Tutoriais',
    'legal': 'Legal',
    'termos-de-uso': 'Termos de uso',
    'privacidade': 'Privacidade',
    'cookies': 'Cookies',
}

@static_page_routes.route('/<slug>')
def show_page(slug):
    if slug in PAGES:
        return render_template(f'pages/{slug}.html', page_title=PAGES[slug])
    abort(404)
