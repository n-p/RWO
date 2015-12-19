# This program hasn't been tested.
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
        self.base_engine.setoption({'Threads': '1'})
        self.modified_engine.setoption({'Threads': '1'})
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
        #if selected_engine_index == 1:  # only modified engine needs clearing hash!
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
        d1 = self.run_engine(max_depth=4, fen=my_fen, selected_engine_index=1)
        d_max = self.run_engine(max_depth=8, fen=my_fen, selected_engine_index=0)
        # if you use depth 1 for both engines the values should converge to current values.
        return abs(d_max - d1)

    def mse(self, max_samples):
        p = open(self.fens_file)
        s = 0.0
        count = 0
        line = p.readline()
        max_samples *= 1.0
        while line != '' and count < max_samples:
            s += self.find_error(line) / max_samples
            count += 1
            line = p.readline()
        p.close()
        return s

    def tune(self, max_samples, variables_count):
        # These could be best values we got till now (Current numbers or start from something like 50.0).
        best_values = []
        for i in range(variables_count):
            best_values.append(0)
        best_values[0] = 50
        best_values[1] = 50
        best_values[2] = 50
        best_values[3] = 50
        best_values[4] = 50
        best_values[5] = 50

        values = []
        for i in range(variables_count):
            best_values[i] *= 1.0  # casting!
            values.append(0.0)

        p = open('result.txt', 'a+')
        p.writelines('\n------------New session started-----------------\n')
        for i in range(variables_count):
            self.modified_engine.setoption({('vAlUe' + i.__repr__()): best_values[i]})
        self.modified_engine.ucinewgame(async_callback=False)
        min_error = error = self.mse(max_samples)
        p.writelines('error: ' + error.__repr__() + '\n---------------------------------------\n')
        print('error: ' + error.__repr__())

        for epoch in range(10000):
            print('Epoch:' + epoch.__repr__())
            # update values
            for i in range(variables_count):
                # Tuning variables supposed to be vAlUe0, vAlUe2, etc.
                value_name = 'vAlUe' + i.__repr__()
                values[i] = best_values[i] + 2.0 * (random.random() - 0.5) * 30.0
                if values[i] < -1000.0:
                    values[i] = -1000.0
                if values[i] > 1000.0:
                    values[i] = 1000.0
                new_value = round(values[i])
                self.modified_engine.setoption({value_name: new_value})
            self.modified_engine.ucinewgame(async_callback=False)
            error = self.mse(max_samples)
            print('error: ' + error.__repr__())
            if error < min_error:
                for i in range(variables_count):
                    best_values[i] = values[i]
                    new_value = round(values[i])
                    p.writelines('best_values[' + i.__repr__() + '] = ' + new_value.__repr__() + '\n')
                min_error = error
                p.write('Epoch:' + epoch.__repr__() + '\nValues:\n')
                p.writelines('Found better values!\n')
                print('Found better values! ')
				p.writelines('error: ' + error.__repr__() + '\n---------------------------------------\n')
            print('----------------------------------------')
            if error == 0:
                break
        p.close()


def main():
    rw = RandomWalking()
    rw.tune(2000, 6)


main()
