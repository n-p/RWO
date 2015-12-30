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

    def run_engine(self, epd, max_depth=0, move_time=0):
        self.modified_engine.setoption({'Clear': 'Hash'})
        board = Board()
        board.set_epd(epd)
        self.modified_engine.position(board)
        if max_depth != 0:
            self.modified_engine.go(depth=max_depth, async_callback=False)
        else:
            self.modified_engine.go(movetime=move_time, async_callback=False)
        while self.modified_engine.bestmove is None:
            pass
        result = self.info_handler_modified.info["score"][1].cp
        return result

    def mae(self, epd_file_path, max_samples):
        # EPD file format is: odd lines is EPD position even lines is ideal outputs
        epd_file = open(epd_file_path)
        s = 0.0
        count = 0
        epd_line = epd_file.readline()     # EPD position
        max_samples *= 1.0
        while epd_line != '' and count < max_samples:
            cp = int(epd_file.readline())     # ideal values in centipawn
            error = abs(self.run_engine(epd=epd_line, move_time=50) - cp)
            s += error / max_samples
            count += 1
            epd_line = epd_file.readline()     # EPD position
        epd_file.close()
        return s

    def tune(self, epd_file_path, max_samples, number_of_variables_have_chance):
        values = []
        for i in range(self.variables_count):
            values.append(0.0)

        log_file = open('result.txt', 'a+')
        log_file.writelines('\n------------New session started-----------------\n')
        for i in range(self.variables_count):
            self.modified_engine.setoption({self.variable_names[i]: self.best_values[i]})
            values[i] = self.best_values[i]
        self.modified_engine.ucinewgame(async_callback=False)
        min_error = error = self.mae(epd_file_path, max_samples)
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
            error = self.mae(epd_file_path, max_samples)
            print('Error: ' + error.__repr__())
            if error < min_error:
                for i in range(self.variables_count):
                    diff = values[i] - self.best_values[i]
                    self.best_values[i] = values[i]
                    new_value = round(values[i])
                    log_file.writelines(self.variable_names[i] + ' = ' + new_value.__repr__())
                    if diff > 0:
                        log_file.writelines(' <- increased')
                    elif diff < 0:
                        log_file.writelines(' <- decreased')
                    log_file.writelines('\n')
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
    # EPD file, sample size, how many variables have a chance to change in each iteration
    rw.tune("tcec-ccrl.epd", 1200, 3)


main()
