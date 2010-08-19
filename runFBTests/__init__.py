import sys
import execute_fb_tests

def cli_run():
    execute_fb_tests.main(sys.argv[1:])

def cli_update():
    fb_update.main(sys.argv[1:])