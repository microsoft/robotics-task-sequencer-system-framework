# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------


class Blackboard:

    def __init__(self):
        self.board = {}

    def clearBoard(self):
        self.board = {}

    def setBoardVariable(self, key: str, value):
        if key == "":
            print("Blackboard: ignoring key as empty string")
            return
        self.board[key] = value

    def getBoardVariable(self, key: str):
        if key in self.board: return self.board[key]
        else:
            print("Blackborad: get on unknown variable %s" % key)
            return None