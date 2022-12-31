import multiprocessing as mp
import time

def f(conn):
    time.sleep(3)
    conn.send(32)
    conn.close()

if __name__ == '__main__':
    par_conn, child_conn = mp.Pipe()
    p = mp.Process(target=f, args=(child_conn, ))
    p.start()
    val = par_conn.recv()
    print(f'{val = }')
    #p.join()
