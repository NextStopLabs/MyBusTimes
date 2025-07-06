class LogCORSHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Log CORS headers
        print("== CORS Headers ==")
        print("Origin:", request.headers.get('Origin'))
        print("Access-Control-Allow-Origin:", response.get('Access-Control-Allow-Origin'))
        print("Access-Control-Allow-Credentials:", response.get('Access-Control-Allow-Credentials'))
        print("==================")

        return response
