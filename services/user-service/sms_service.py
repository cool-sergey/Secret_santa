import logging
import random
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SMSService:
    @staticmethod
    def send_code(phone: str) -> str:
        code = f"{random.randint(100000, 999999)}"        
        logger.info("="*50)
        logger.info(f"📱 SMS отправлено на {phone}")
        logger.info(f"🔑 Код: {code}")
        logger.info("="*50)
        
        return code
