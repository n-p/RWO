from chess import pgn
import re


class PGNToEPD:
    def __init__(self, pgn_file_path, epd_file_path):
        self.pgn_file = open(pgn_file_path)
        self.epd_file = open(epd_file_path, 'a+')

    def __del__(self):
        self.pgn_file.close()
        self.epd_file.close()

    @staticmethod
    def find_evaluation_in_comment(position, event):
        comment = position.comment
        if event == 'ccrl':
            comment = comment.replace('\n', '')
            comment = re.sub(r"/.*", "", comment)
            comment = re.sub(r"\[[^\[\]]*\]", "", comment)
            comment = re.sub(r"\([^\(\)]*\)", "", comment)
            comment = re.sub(r"\d+s", "", comment)
            comment = re.sub(r" +", "", comment)
        elif event == 'tcec':
            comment = re.sub(r"[^w]*(w[^v])*wv=", "", comment)
            comment = re.sub(r",.*", "", comment)
            if len(comment) > 5 or 'book' in comment:
                comment = ''
        try:
            return float(comment)
        except ValueError:
            return None

    @staticmethod
    def get_winning_side(game):
        # Result is 0-1 or 1-0 or 1/2-1/2
        if game.headers["Result"] == '1-0':
            winning_side = 1
        elif game.headers["Result"] == '0-1':
            winning_side = -1
        elif game.headers["Result"] == '1/2-1/2':
            winning_side = 0
        else:
            raise Exception('Error: There is a problem in one of the results!')
        return winning_side

    @staticmethod
    def get_our_side(game):
        if 'stockfish' in game.headers["White"].lower():
            our_side = 1
        elif 'stockfish' in game.headers["Black"].lower():
            our_side = -1
        else:
            our_side = 0  # if we are not on either side
        return our_side

    @staticmethod
    def opponent_is_right(winning_side, our_side, our_eval, opponent_eval):
        if winning_side != our_side:
            ideal_evaluation = winning_side * 1000.0
            if abs(opponent_eval - ideal_evaluation) < abs(our_eval - ideal_evaluation):
                return True
            else:
                return False

    def process(self):
        while True:
            game = pgn.read_game(self.pgn_file)
            if game is None:  # It's end of the pgn file
                break

            # This is a new game
            our_side = self.get_our_side(game)
            if our_side == 0:
                continue
            if 'ccrl' in game.headers["Event"].lower():
                event = 'ccrl'
            if 'tcec' in game.headers["Event"].lower():
                event = 'tcec'
            winning_side = self.get_winning_side(game)

            pos1 = game.end()
            # We are reading 2 consecutive moves to get our eval and opponent's eval
            pos2 = pos1.parent
            counter = 0
            while pos1 is not None and pos2 is not None and counter <= 20:
                if event == 'ccrl':
                    ev1 = self.find_evaluation_in_comment(pos1, 'ccrl')
                    ev2 = self.find_evaluation_in_comment(pos2, 'ccrl')
                elif event == 'tcec':
                    ev1 = self.find_evaluation_in_comment(pos1, 'tcec')
                    ev2 = self.find_evaluation_in_comment(pos2, 'tcec')
                turn1 = 1 if pos1.board().turn else -1
                if ev1 is not None and ev2 is not None:
                    our_eval = ev1 if turn1 == our_side else ev2
                    opp_eval = ev2 if turn1 == our_side else ev1
                    if self.opponent_is_right(winning_side, our_side, our_eval, opp_eval):
                        self.epd_file.write(pos1.board().epd() + '\n')
                        self.epd_file.write(str(winning_side * 123) + '\n')
                # get previous position
                pos1 = pos2
                pos2 = pos1.parent
                counter += 1


def main():
    p = PGNToEPD("input.pgn", "output.epd")
    p.process()


main()
