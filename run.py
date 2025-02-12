
from dotenv import load_dotenv
load_dotenv()
from api.main import app

if __name__ == "__main__":
    import uvicorn
    from api.db import settings
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)