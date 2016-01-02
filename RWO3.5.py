# Author: N. Paeideh

import random
from chess import uci
from chess import Board
import subprocess
import platform

IS_WINDOWS = 'windows' in platform.system().lower()


class RandomWalking:
    # For clarity
    modified_file_name = ''
    modified_engine = None
    info_handler_modified = None
    variables_count = 0
    variable_names = []
    best_values = []
    range = []  # [[min0,max0], [min1, max1], ...]
    train_positions_evals = []
    test_positions_evals = []

    def __init__(self, epd_file_path, max_samples, test_fraction):
        if IS_WINDOWS:
            self.modified_file_name = 'stockfish.exe'
        else:
            self.modified_file_name = './stockfish'
        self.detect_variable_names()
        self.open_engine_process()
        self.modified_engine.setoption({'Threads': '1'})
        self.modified_engine.setoption({'Hash': '128'})
        self.get_all_positions(epd_file_path, max_samples, test_fraction)

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

    def get_all_positions(self, epd_file_path, max_samples, test_fraction):
        # EPD file format is: odd lines is EPD position even lines is ideal outputs
        epd_file = open(epd_file_path)
        count = 0
        epd_line = epd_file.readline()  # EPD position
        while len(epd_line) > 8 and count < max_samples:
            cp = int(epd_file.readline())  # ideal values in centipawn
            self.train_positions_evals.append([epd_line, cp])
            epd_line = epd_file.readline()  # EPD position
            count += 1
        epd_file.close()

        # We have all sample in self.train_positions_evals now
        samples_count = len(self.train_positions_evals)
        for _ in range(1, int(test_fraction * samples_count)):
            r = random.randint(0, samples_count - 1)
            temp = self.train_positions_evals[r]
            self.test_positions_evals.append(temp)
            self.train_positions_evals.remove(temp)
            samples_count -= 1

    def fast_mae(self, fraction):
        # We are using a fraction of samples
        s = 0.0
        samples_count = float(len(self.train_positions_evals))
        samples_count2 = fraction * samples_count
        for i in range(int(samples_count2)):
            r = random.randint(0, samples_count - 1)
            pos, cp = self.train_positions_evals[r]
            error = abs(self.run_engine(epd=pos, move_time=50) - cp)
            s += error / samples_count2
        return s

    def mae(self, position_evals):      # It has to know we want to calculate mae for train or test
        # mae for all samples
        s = 0.0
        samples_count = float(len(position_evals))
        for pos, cp in position_evals:
            error = abs(self.run_engine(epd=pos, move_time=50) - cp)
            s += error / samples_count
        return s

    def tune(self, number_of_variables_have_chance):
        values = []
        for i in range(self.variables_count):
            values.append(0.0)

        log_file = open('result.txt', 'a+')
        log_file.writelines('\n------------New session started-----------------\n')
        for i in range(self.variables_count):
            self.modified_engine.setoption({self.variable_names[i]: self.best_values[i]})
            values[i] = self.best_values[i]
        self.modified_engine.ucinewgame(async_callback=False)
        train_min_error = error = self.mae(self.train_positions_evals)
        test_min_error = self.mae(self.test_positions_evals)
        log_file.writelines('Error before first iteration: ' + error.__repr__() +
                            "\n---------------------------------------\n")
        print('Error before first iteration: ' + error.__repr__())
        log_file.close()

        for iteration in range(1, 10000):
            print('Iteration:' + iteration.__repr__())
            for i in range(self.variables_count):
                # Smaller steps
                min_ = self.best_values[i] - 50 if self.best_values[i] - 50 >= self.range[i][0] else self.range[i][0]
                max_ = self.best_values[i] + 50 if self.best_values[i] + 50 <= self.range[i][1] else self.range[i][1]
                # Only limited number of variables have a chance. 3 in here
                if random.randint(1, self.variables_count) > number_of_variables_have_chance:
                    values[i] = self.best_values[i]
                else:
                    values[i] = random.randint(min_, max_)
                    self.modified_engine.setoption({self.variable_names[i]: values[i]})
            self.modified_engine.ucinewgame(async_callback=False)
            error = self.fast_mae(0.1)
            print('Error: ' + error.__repr__())
            # Kind of MLFQ
            if error < train_min_error:
                # Make sure before reporting
                print("Let's test it again with more samples to make sure ...")
                error = self.fast_mae(0.1)
                print('Error: ' + error.__repr__())
                if error < train_min_error:
                    print("Let's test it again with even more samples ...")
                    error = self.fast_mae(0.3)
                    print('Error: ' + error.__repr__())
                    if error < train_min_error:
                        print("Ok! Let's test it with all training samples ...")
                        error = self.mae(self.train_positions_evals)
                        print('Error: ' + error.__repr__())
                        if error < train_min_error:
                            test_error = self.mae(self.test_positions_evals)
                            if test_error < test_min_error:
                                test_min_error = test_error
                                log_file = open('result.txt', 'a+')
                                # Now we are sure
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
                                train_min_error = error
                                log_file.write('Iteration:' + iteration.__repr__() + '\nValues:\n')
                                log_file.writelines('Better values!\n')
                                print('We found better values!')
                                log_file.writelines(
                                    'Error: ' + error.__repr__() + '\n---------------------------------------\n')
                                log_file.close()
                            else:
                                print("Failed in test set!")
            print('----------------------------------------')
            if error == 0:
                print('Congrats!')
                break


def main():
    rw = RandomWalking("sts-arasan-7200ms-stockfish-beta2.epd", 1000000, 0.1)
    rw.tune(2)


main()
