from app import create_app
import argparse

def main():
    parser = argparse.ArgumentParser(description='Run the Media Encoder Service')
    parser.add_argument('--port', type=int, default=5000, help='Port to run the service on')
    args = parser.parse_args()

    app = create_app()
    app.run(host='0.0.0.0', port=args.port, debug=True)

if __name__ == '__main__':
    main()
