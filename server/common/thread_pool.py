import threading
import queue

class ThreadPool:
    def __init__(self, num_workers, max_queue=0):
        self.num_workers = num_workers
        self.task_queue = queue.Queue(maxsize=max_queue)
        self.workers = []
        self._init_workers()

    def _init_workers(self):
        for _ in range(self.num_workers):
            worker = threading.Thread(target=self._worker_loop)
            worker.start()
            self.workers.append(worker)

    def _worker_loop(self):
        while True:
            func, args = self.task_queue.get()
            try:
                if func is None:
                    break
                func(*args)
            except Exception as e:
                print(f"Error processing task: {e}")
            finally:
                self.task_queue.task_done()

    def submit(self, func, *args):
        self.task_queue.put((func, args))
        
    def stop(self):
        for _ in range(self.num_workers):
            self.task_queue.put((None, None))
        self.task_queue.join()
        for worker in self.workers:
            worker.join()