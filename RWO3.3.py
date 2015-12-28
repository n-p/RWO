import random
from chess import uci
from chess import Board
import subprocess
import platform

IS_WINDOWS = 'windows' in platform.system().lower()


class RandomWalking:
    modified_file_name = ''
    # for clarity
    modified_engine = None
    info_handler_modified = None
    variables_count = 0
    variable_names = []
    best_values = []
    range = []  # [[min0,max0], [min1, max1], ...]

    def __init__(self):
        if IS_WINDOWS:
            self.modified_file_name = 'stockfish.exe'
        else:
            self.modified_file_name = './stockfish'
        self.detect_variable_names()
        self.open_engine_process()
        self.modified_engine.setoption({'Threads': '1'})

    def detect_variable_names(self):
        try:
            result = []
            p = subprocess.Popen([self.modified_file_name, 'uci'], stdout=subprocess.PIPE, universal_newlines=True)
            p.stdout.readline()
            while True:
                line = p.stdout.readline()
                if 'id name' in line:
                    break
                result.append(line.split(','))
            # TODO: Add exception handling logic here
        finally:
            # TODO: it's assigned?
            p.kill()
        # We have all variable names now
        self.variables_count = len(result)
        for i in range(self.variables_count):
            self.variable_names.append(result[i][0])
            self.best_values.append(float(result[i][1]))
            self.range.append([int(result[i][2]), int(result[i][3])])

    def open_engine_process(self):
        self.modified_engine = uci.popen_engine(self.modified_file_name)
        self.info_handler_modified = uci.InfoHandler()
        self.modified_engine.info_handlers.append(self.info_handler_modified)

    def __del__(self):
        self.modified_engine.terminate(async_callback=False)

    def run_engine(self, fen, max_depth=0, move_time=0):
        self.modified_engine.setoption({'Clear': 'Hash'})
        board = Board()
        board.set_fen(fen)
        self.modified_engine.position(board)
        if max_depth != 0:
            self.modified_engine.go(depth=max_depth, async_callback=False)
        else:
            self.modified_engine.go(movetime=move_time, async_callback=False)
        while self.modified_engine.bestmove is None:
            pass
        result = self.info_handler_modified.info["score"][1].cp
        return result

    def mae(self, fen_file_path, max_samples):
        # FEN file format is: odd lines is FEN position even lines is ideal outputs
        fen_file = open(fen_file_path)
        s = 0.0
        count = 0
        fen_line = fen_file.readline()     # FEN position
        max_samples *= 1.0
        while fen_line != '' and count < max_samples:
            cp = int(fen_file.readline())     # ideal values in centipawn
            error = abs(self.run_engine(fen=fen_line, move_time=50) - cp)
            s += error / max_samples
            count += 1
            fen_line = fen_file.readline()     # FEN position
        fen_file.close()
        return s

    def tune(self, fen_file_path, max_samples, number_of_variables_have_chance):
        values = []
        for i in range(self.variables_count):
            values.append(0.0)

        log_file = open('result.txt', 'a+')
        log_file.writelines('\n------------New session started-----------------\n')
        for i in range(self.variables_count):
            self.modified_engine.setoption({self.variable_names[i]: self.best_values[i]})
            values[i] = self.best_values[i]
        self.modified_engine.ucinewgame(async_callback=False)
        min_error = error = self.mae(fen_file_path, max_samples)
        log_file.writelines('Error before first iteration: ' + error.__repr__() + '\n---------------------------------------\n')
        print('Error before first iteration: ' + error.__repr__())
        log_file.close()

        for iteration in range(1, 10000):
            log_file = open('result.txt', 'a+')
            print('Iteration:' + iteration.__repr__())
            for i in range(self.variables_count):
                # Smaller steps
                min_ = self.best_values[i] - 20 if self.best_values[i] - 20 >= self.range[i][0] else self.range[i][0]
                max_ = self.best_values[i] + 20 if self.best_values[i] + 20 <= self.range[i][1] else self.range[i][1]
                # Only limited number of variables have a chance. 3 in here
                if random.randint(1, self.variables_count) > number_of_variables_have_chance:
                    values[i] = self.best_values[i]
                else:
                    values[i] = random.randint(min_, max_)
                    self.modified_engine.setoption({self.variable_names[i]: values[i]})
            self.modified_engine.ucinewgame(async_callback=False)
            error = self.mae(fen_file_path, max_samples)
            print('Error: ' + error.__repr__())
            if error < min_error:
                for i in range(self.variables_count):
                    self.best_values[i] = values[i]
                    new_value = round(values[i])
                    log_file.writelines(self.variable_names[i] + ' = ' + new_value.__repr__() + '\n')
                min_error = error
                log_file.write('Iteration:' + iteration.__repr__() + '\nValues:\n')
                log_file.writelines('Found better values!\n')
                print('Found better values! ')
                log_file.writelines('Error: ' + error.__repr__() + '\n---------------------------------------\n')
            print('----------------------------------------')
            if error == 0:
                break
            log_file.close()


def main():
    rw = RandomWalking()
    # FEN file, sample size, how many variables have a chance to change in each iteration
    rw.tune("analyzed-6500-mixed.txt", 6500, 3)


main()
