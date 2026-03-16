import lzma
import pickle

from datetime import datetime


class Scoreboard:
    def __init__(self) -> None:
        self.scores = {}
        pass

    def add_score(self, new_score):
        if self.is_score_relevant(new_score=new_score):
            self.scores.update({datetime.now(): new_score})

    def is_score_relevant(self, new_score) -> bool:
        score_to_replace = 0
        for score in self.scores:
            if new_score >= self.scores[score] and self.scores[score] >= score_to_replace:
                score_to_replace = score
        if len(self.scores) < 1:
            return True
        try:
            if self.scores[score_to_replace] > 0 and len(self.scores) >= 10:
                self.scores.pop(score_to_replace)
                return True
        except KeyError:
            if len(self.scores) <= 10:
                return True
            else:
                return False

        

        


    def save(self):
        save_data = lzma.compress(pickle.dumps(self))
        with open("scoreboard.sav", "wb") as f:
            f.write(save_data)

    @staticmethod
    def load_scoreboard():
        try:
            with open("scoreboard.sav", "rb") as f:
                board = ""
                board = pickle.loads(lzma.decompress(f.read()))
                assert isinstance(board, Scoreboard)
                return board
        except FileNotFoundError:
            return Scoreboard()
