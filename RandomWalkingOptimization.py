# This program needs python-chess to run
import random
from chess import uci
from chess import Board


class RandomWalking:
    base_file_name = './base'
    modified_file_name = './stockfish'
    fens_file = "book.epd"  # files contains FENs (middle game or endgame).
    # to get rid of some warnings(and clarity)
    base_engine = None
    modified_engine = None
    info_handler_modified = None

    def __init__(self):
        self.open_engine_process()
        self.base_engine = uci.popen_engine(self.base_file_name)
        self.info_handler_base = uci.InfoHandler()
        self.base_engine.info_handlers.append(self.info_handler_base)
        self.base_engine.setoption({'Threads': '2'})
        self.modified_engine.setoption({'Threads': '2'})
        # for base engine selected_engine is 0
        # for modified engine selected_engine is 1
        self.selected_engine = self.base_engine
        self.selected_engine_index = 0

    def open_engine_process(self):
        self.modified_engine = uci.popen_engine(self.modified_file_name)
        self.info_handler_modified = uci.InfoHandler()
        self.modified_engine.info_handlers.append(self.info_handler_modified)

    def __del__(self):
        self.base_engine.terminate(async_callback=False)
        self.modified_engine.terminate(async_callback=False)

    def select_engine(self, num):
        if num == 0:
            self.selected_engine = self.base_engine
            self.selected_engine_index = 0
        else:
            self.selected_engine = self.modified_engine
            self.selected_engine_index = 1

    def run_engine(self, max_depth, fen, selected_engine_index):
        self.select_engine(selected_engine_index)
        # I modified uci.py file for clearing hash
        # if not (name == 'Clear' and value == 'Hash'):
        #     builder.append("value")
        if selected_engine_index == 1:  # only modified engine needs clearing hash!
            self.selected_engine.setoption({'Clear': 'Hash'})
        board = Board()
        board.set_fen(fen)
        self.selected_engine.position(board)
        self.selected_engine.go(depth=max_depth, async_callback=False)
        while self.selected_engine.bestmove is None:
            pass
        if selected_engine_index == 0:
            result = self.info_handler_base.info["score"][1].cp
        else:
            result = self.info_handler_modified.info["score"][1].cp
        return result

    def find_error(self, my_fen):
        d1 = self.run_engine(max_depth=1, fen=my_fen, selected_engine_index=1)
        d_max = self.run_engine(max_depth=4, fen=my_fen, selected_engine_index=0)
        # if you use depth 1 for both engines the values converge to current values.
        return abs(d_max - d1)

    def mse(self, max_samples):
        p = open(self.fens_file)
        s = 0.0
        count = 0
        line = p.readline()
        while line != '' and count < max_samples:
            s += 1.0 * self.find_error(line) / max_samples
            count += 1
            line = p.readline()
        p.close()
        return s

    def tune(self, max_samples, variables_count):
        # These could be best values we got till now (Current numbers or start from something like 50.0).
        # These specific values is from Weights array from evaluate.cpp as an example
        # {266, 334}, {214, 203}, {193, 262}, {47, 0}, {330, 0}, {404, 241}
        best_values = []
        for i in range(variables_count):
            best_values.append(0)
        best_values[0] = 266
        best_values[1] = 214
        best_values[2] = 193
        best_values[3] = 47
        best_values[4] = 330
        best_values[5] = 404

        values = []
        for i in range(variables_count):
            best_values[i] *= 1.0   # for performance!
            values.append(0.0)

        p = open('result.txt', 'a+')
        p.writelines('\n------------New session started-----------------\n')
        min_error = 1000.0
        for epoch in range(10000):
            p.write('Epoch:' + epoch.__repr__() + '\n')
            print('Epoch:' + epoch.__repr__())
            p.write('Values:\n')
            # update values
            for i in range(variables_count):
                # This program suppose tuning values have names like vAlUe0, vAlUe2, etc.
                value_name = 'vAlUe' + i.__repr__()
                if epoch != 0:
                    values[i] = best_values[i] + 2.0 * (random.random() - 0.5) * 5.0
                else:
                    values[i] = best_values[i]
                # or you can use error instead of 10
                new_value = values[i]
                new_value = round(new_value) if new_value > -1000 else -1000
                new_value = round(new_value) if new_value < 1000 else 1000
                self.modified_engine.setoption({value_name: new_value})
                self.modified_engine.ucinewgame(async_callback=False)
                p.writelines('best_values[' + i.__repr__() + '] = ' + new_value.__repr__() + '.0\n')
            error = self.mse(max_samples)
            p.writelines('error: ')
            print('error: ')
            print(error)
            if error < min_error:
                for i in range(variables_count):
                    best_values[i] = values[i]
                min_error = error
                p.writelines('Found better values!\n')
                print('Found better values! ')
            p.writelines(error.__repr__() + '\n---------------------------------------\n')
            print('--------------------------------------------------')
            if error == 0:
                break
        p.close()


def main():
    rw = RandomWalking()
    rw.tune(1000, 6)


main()
