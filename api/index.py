from flask import Flask, render_template, jsonify, request
import requests
import os

app = Flask(__name__, template_folder='../templates', static_folder='../static')

MANGADEX_API = 'https://api.mangadex.org'

HEADERS = {
    'User-Agent': 'HanaReader/1.0'
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/manga/<manga_id>')
def manga_detail(manga_id):
    return render_template('manga.html', manga_id=manga_id)

@app.route('/read/<manga_id>/<chapter_id>')
def reader(manga_id, chapter_id):
    return render_template('reader.html', manga_id=manga_id, chapter_id=chapter_id)

@app.route('/api/search')
def search():
    query = request.args.get('q', '')
    limit = request.args.get('limit', 20)
    offset = request.args.get('offset', 0)
    
    try:
        params = {
            'title': query,
            'limit': limit,
            'offset': offset,
            'includes[]': ['cover_art', 'author', 'artist'],
            'order[relevance]': 'desc',
            'availableTranslatedLanguage[]': ['pt-br']  # Apenas PT-BR
        }
        r = requests.get(f'{MANGADEX_API}/manga', params=params, headers=HEADERS, timeout=10)
        return jsonify(r.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Novo endpoint: Listar por categoria/tag
@app.route('/api/browse')
def browse():
    try:
        tag = request.args.get('tag', '')
        letter = request.args.get('letter', '')
        limit = request.args.get('limit', 20)
        offset = request.args.get('offset', 0)
        
        params = {
            'limit': limit,
            'offset': offset,
            'includes[]': ['cover_art', 'author', 'artist'],
            'availableTranslatedLanguage[]': ['pt-br'],  # Apenas PT-BR
            'order[followedCount]': 'desc'
        }
        
        # Filtro por tag
        if tag:
            params['includedTags[]'] = [tag]
        
        # Filtro por letra inicial do título
        if letter:
            params['title'] = f'^{letter}'
        
        r = requests.get(f'{MANGADEX_API}/manga', params=params, headers=HEADERS, timeout=10)
        return jsonify(r.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Endpoint para listar todas as tags disponíveis
@app.route('/api/tags')
def get_tags():
    try:
        r = requests.get(f'{MANGADEX_API}/manga/tag', headers=HEADERS, timeout=10)
        return jsonify(r.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/manga/<manga_id>')
def manga_info(manga_id):
    try:
        params = {'includes[]': ['cover_art', 'author', 'artist', 'tag']}
        r = requests.get(f'{MANGADEX_API}/manga/{manga_id}', params=params, headers=HEADERS, timeout=10)
        return jsonify(r.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/manga/<manga_id>/chapters')
def manga_chapters(manga_id):
    try:
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        params = {
            'manga': manga_id,
            'translatedLanguage[]': ['pt-br'],  # Apenas PT-BR
            'order[chapter]': 'asc',
            'limit': limit,
            'offset': offset,
            'includes[]': ['scanlation_group']
        }
        
        r = requests.get(f'{MANGADEX_API}/chapter', params=params, headers=HEADERS, timeout=10)
        return jsonify(r.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chapter/<chapter_id>/pages')
def chapter_pages(chapter_id):
    try:
        r = requests.get(f'{MANGADEX_API}/at-home/server/{chapter_id}', headers=HEADERS, timeout=10)
        data = r.json()
        
        if 'baseUrl' in data:
            base_url = data['baseUrl']
            chapter_hash = data['chapter']['hash']
            pages = data['chapter']['data']
            
            # Gera URLs de todas as páginas
            urls = [f'{base_url}/data/{chapter_hash}/{p}' for p in pages]
            return jsonify({'pages': urls, 'total': len(urls)})
        
        return jsonify({'error': 'Chapter not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chapter/<chapter_id>')
def chapter_info(chapter_id):
    try:
        params = {'includes[]': ['manga', 'scanlation_group']}
        r = requests.get(f'{MANGADEX_API}/chapter/{chapter_id}', params=params, headers=HEADERS, timeout=10)
        return jsonify(r.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/cover/<manga_id>/<cover_file>')
def proxy_cover(manga_id, cover_file):
    try:
        url = f'https://uploads.mangadex.org/covers/{manga_id}/{cover_file}.256.jpg'
        r = requests.get(url, headers=HEADERS, stream=True, timeout=10)
        
        from flask import Response
        return Response(
            r.content,
            content_type=r.headers.get('content-type', 'image/jpeg')
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
