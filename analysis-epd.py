# How to use:
# Change your engine's name to "base.exe" (on windows) and "base" on other platforms
# Give these arguments to evaluate_all_positions method
# 1- Change epd file's path to your file's (epd file should contain only EPDs)
# 2- Sample size
# 3- move time for each position in milliseconds
# The output file is "analyzed.txt" that contains epd positions and evaluations in separate lines.

from chess import uci
from chess import Board
import platform

IS_WINDOWS = 'windows' in platform.system().lower()


class Analysis:
    base_file_name = ''
    base_engine = None
    info_handler_modified = None

    def __init__(self):
        if IS_WINDOWS:
            self.base_file_name = 'base.exe'
        else:
            self.base_file_name = './base'
        self.base_engine = uci.popen_engine(self.base_file_name)
        self.info_handler_base = uci.InfoHandler()
        self.base_engine.info_handlers.append(self.info_handler_base)
        self.base_engine.setoption({'Threads': '2'})
        self.base_engine.setoption({'Hash': '2048'})

    def __del__(self):
        self.base_engine.terminate(async_callback=False)

    def run_engine(self, epd, move_time):
        #self.base_engine.setoption({'Clear': 'Hash'})  # We don't need to clear hash
        board = Board()
        board.set_epd(epd)
        self.base_engine.position(board)
        self.base_engine.go(movetime=move_time, async_callback=False)
        while self.base_engine.bestmove is None:
            pass
        return self.info_handler_base.info["score"][1].cp

    def evaluate_all_positions(self, epd_file_path, output_file_path, max_samples, move_time):
        print("1000 positions will take " + str(move_time / 3600) + " hour(s) to complete.")
        epd = open(epd_file_path)
        a_file = open(output_file_path, 'w')
        count = 0
        line = epd.readline()
        while len(line) > 8 and count < max_samples:
            line = line.replace('\n', '')
            result = self.run_engine(line, move_time)
            a_file.write(line + '\n' + result.__repr__() + '\n')
            count += 1
            if count % 1000 == 0:
                print(str(count) + ' positions processed.')
            line = epd.readline()
        epd.close()
        a_file.close()
        print("Finished!")


def main():
    rw = Analysis()
    rw.evaluate_all_positions("AllTestSuites.epd", "analyzed.txt", 1000000, 2 * 3600)


main()
