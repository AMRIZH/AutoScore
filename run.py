"""
AutoScoring Application Entry Point
Lab FKI Universitas Muhammadiyah Surakarta
"""

import os
from app import create_app

# Create application instance
app = create_app()

if __name__ == '__main__':
    # Get configuration from environment
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    
    print(f"""
    ╔══════════════════════════════════════════════════════════════╗
    ║                     AutoScoring v1.0                         ║
    ║          Lab FKI Universitas Muhammadiyah Surakarta          ║
    ║              Program Studi Informatika                       ║
    ╠══════════════════════════════════════════════════════════════╣
    ║  Server berjalan di: http://{host}:{port}                    ║
    ║  Mode Debug: {'Aktif' if debug else 'Nonaktif':^10}          ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    app.run(host=host, port=port, debug=debug)
