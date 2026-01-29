from fastapi import FastAPI, Request
import time
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s, %(name)-33s, %(levelname)-5s, %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

app = FastAPI()
logger = logging.getLogger(__name__)
logger.info("\n\nNEW INSTANCE--------------------------------------------")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Process the request
    response = await call_next(request)
    
    process_time = (time.time() - start_time) * 1000
    formatted_process_time = '{0:.2f}'.format(process_time)
    
    logger.info(
        f"Path: {request.url.path} "
        f"Method: {request.method} "
        f"Status: {response.status_code} "
        f"Duration: {formatted_process_time}ms"
    )
    
    return response

@app.get("/")
def status_check():
    return {"status": "ok"}


