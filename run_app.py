import logging
import sys

from pokemon_go_collection import app as app_m
from pokemon_go_collection import logging_setup as logging_setup_m

# `streamlit run` executes this file as `__main__` at every rerun.
is_debug = "--debug" in sys.argv
logging_setup_m.setup_logging(
    logging_level=logging.DEBUG if is_debug else logging.INFO,
    display_logger_name=is_debug,
)
app_m.main()
