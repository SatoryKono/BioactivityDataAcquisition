# _child_runner.py
import multiprocessing

def run_child(target, args):
    p = multiprocessing.Process(target=target, args=args)
    p.start()
    p.join()
    return p.exitcode
