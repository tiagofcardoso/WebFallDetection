from app import create_app
import sys
import os

# Adicionar o diretório raiz e o diretório app ao PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'app'))


app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
