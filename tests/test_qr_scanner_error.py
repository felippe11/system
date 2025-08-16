import subprocess
import textwrap
from pathlib import Path


def test_status_element_updates_when_html5qrcode_missing():
    repo_root = Path(__file__).resolve().parents[1]
    script = textwrap.dedent(
        """
        import { JSDOM } from 'jsdom';
        import { initScanner } from './static/js/qr_scanner.js';

        const dom = new JSDOM(`<div id="qr-video"></div><div id="scan-status"></div>`, { url: 'http://localhost' });
        global.window = dom.window;
        global.document = dom.window.document;

        const statusElement = document.getElementById('scan-status');

        try {
          await initScanner('qr-video', () => {});
          statusElement.textContent = 'success';
        } catch (err) {
          statusElement.innerHTML = `<span class=\"text-danger\">${err.message || err}</span>`;
        }
        console.log(statusElement.innerHTML);
        """
    )
    result = subprocess.run(
        ['node', '--input-type=module', '-e', script],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=True,
    )
    assert 'text-danger' in result.stdout
