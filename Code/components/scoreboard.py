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
        if len(self.scores) < 10:
            return True

        lowest = min(self.scores, key=self.scores.get)
        if new_score > self.scores[lowest]:
            self.scores.pop(lowest)
            return True
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
