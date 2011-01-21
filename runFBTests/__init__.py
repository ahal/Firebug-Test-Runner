import sys
import execute_fb_tests
import fb_update

def cli_run():
    execute_fb_tests.cli(sys.argv[1:])

def cli_update():
    fb_update.main(sys.argv[1:])
