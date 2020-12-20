import logging.config
import os
from pathlib import Path

cwd_path = Path(os.getcwd())
log_path_str = str(cwd_path / "clutchless.log")

logging_conf_file = Path(__file__).parent / "logging.conf"
logging.config.fileConfig(logging_conf_file, defaults={'logfilename': log_path_str})
logger = logging.getLogger(__name__)
logger.info("configured logger")
