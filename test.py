from typing import List
import sys
import chess
from multiprocessing import Process, Queue
import chess.engine
'''
game = pgn.Game()
game.headers["Event"] = "Andromeda Testing Game"
game.headers["Site"] = "Somewhere"
game.headers["Date"] = f"{datetime.date.today().year}.{datetime.date.today().month}.{datetime.date.today().day}"
game.headers["Round"] = "*"
game.headers["White"] = "Andromeda"
game.headers["Black"] = "Andromeda"
game.headers["FEN"] = engine.BOARD.fen()
node = game.add_variation(chess.Move.from_uci("0000"))
'''
evalEngine = chess.engine.SimpleEngine.popen_uci("D:\Chess\Engines\stockfish_15_win_x64_avx2\stockfish_15_x64_avx2.exe")
evalQueue = Queue()
moveQueue = Queue()
minmaxQueue = Queue()
orderedMoveQueue = Queue()
nextMoveQueue = Queue()

def evalBoard(board: chess.Board, limit: float, depth: int) -> float:
    score = evalEngine.analyse(board, chess.engine.Limit(time=limit, depth=depth))["score"].white()
    if score.is_mate():
        returnScore = 1000/int(str(score)[1:])
    elif type(score) is chess.engine.Cp:
        cps = int(str(score))
        if cps == 0:
            returnScore = 0
        else:
            returnScore = 100/int(str(score))
    else:
        returnScore = score
    evalQueue.put(returnScore)


def talk():
    board = chess.Board()
    depth = get_depth()

    while True:
        msg = input()
        command(depth, board, msg)


def command(depth: int, board: chess.Board, msg: str):
    msg = msg.strip()
    tokens = msg.split(" ")
    while "" in tokens:
        tokens.remove("")

    if msg == "quit":
        sys.exit()

    if msg == "uci":
        sys.stdout.write("id name Andromeda\n")
        sys.stdout.write("id author ShadowProgrammer/Wyatt Darley\n")
        sys.stdout.write("uciok\n")
        return

    if msg == "isready":
        sys.stdout.write("readyok\n")
        return

    if msg == "ucinewgame":
        return

    if msg == "show":
        print(board)

    if msg.startswith("move"):
        board.push_uci(tokens[1])

    if msg.startswith("position"):
        if len(tokens) <= 2:
            return

        # Set starting position
        if tokens[1] == "startpos":
            board.reset()
            moves_start = 2
        elif tokens[1] == "fen":
            fen = " ".join(tokens[2:8])
            board.set_fen(fen)
            moves_start = 8
        else:
            return

        # Apply moves
        if len(tokens) <= moves_start or tokens[moves_start] != "moves":
            return

        for move in tokens[(moves_start+1):]:
            board.push_uci(move)

    if msg[0:2] == "go":
        getMoveProcess = Process(target=minimax_root, args=(2, board))
        getMoveProcess.start()
        move = moveQueue.get()
        moveQueue.empty()
        getMoveProcess.join()
        # print(game.game())
        sys.stdout.write(f"bestmove {move}\n")
        return


def get_depth() -> int:
    return 5


MATE_SCORE = 1000000000
MATE_THRESHOLD = 999000000


def next_move(depth: int, board: chess.Board) -> chess.Move:
    nextMoveProcess = Process(target=minimax_root, args=(depth, board))
    nextMoveProcess.start()
    move = moveQueue.get()
    moveQueue.empty()
    nextMoveProcess.join()
    nextMoveQueue.put(move)


def get_ordered_moves(board: chess.Board) -> List[chess.Move]:
    def orderer(move):
        return evalBoard(board, 1, 10)

    in_order = sorted(
        board.legal_moves, key=orderer, reverse=(board.turn == chess.WHITE)
    )
    orderedMoveQueue.put(list(in_order))


def minimax_root(depth: int, board: chess.Board) -> chess.Move:
    maximize = board.turn == chess.WHITE
    best_move = -float("inf")
    if not maximize:
        best_move = float("inf")

    moves = get_ordered_moves(board)
    best_move_found = moves[0]

    for move in moves:
        board.push(move)
        if board.can_claim_draw():
            value = 0.0
        else:
            minmaxProcess = Process(target=minimax, args=(depth - 1, board, -float("inf"), float("inf"), not maximize))
            minmaxProcess.start()
            value = minmaxQueue.get()
            minmaxQueue.empty()
            minmaxProcess.join()
        board.pop()
        try:
            if maximize and value >= best_move:
                best_move = value
                best_move_found = move
            elif not maximize and value <= best_move:
                best_move = value
                best_move_found = move
        except TypeError:
            continue

    moveQueue.put(best_move_found)


def minimax(
    depth: int,
    board: chess.Board,
    alpha: float,
    beta: float,
    is_maximising_player: bool,
):
    if board.is_checkmate():
        minmaxQueue.put(-MATE_SCORE if is_maximising_player else MATE_SCORE)
    elif board.is_game_over():
        minmaxQueue.put(0)

    if depth == 0:
        minmaxQueue.put(evalBoard(board, 1, 10))

    if is_maximising_player:
        best_move = -float("inf")
        moves = get_ordered_moves(board)
        for move in moves:
            board.push(move)
            moveProcess = Process(target=minimax, args=(depth - 1, board, alpha, beta, not is_maximising_player))
            moveProcess.start()
            curr_move = minmaxQueue.get()
            minmaxQueue.empty()
            moveProcess.join()
            print(curr_move)
            board.pop()
            try:
                if curr_move > MATE_THRESHOLD:
                    curr_move -= 1
                elif curr_move < -MATE_THRESHOLD:
                    curr_move += 1
                best_move = max(
                    best_move,
                    curr_move,
                )
            except TypeError:
                minmaxQueue.put(0.0)
            alpha = max(alpha, best_move)
            if beta <= alpha:
                minmaxQueue.put(best_move)
        minmaxQueue.put(best_move)
    else:
        best_move = float("inf")
        moves = get_ordered_moves(board)
        for move in moves:
            board.push(move)
            moveProcess = Process(target=minimax, args=(depth - 1, board, alpha, beta, not is_maximising_player))
            moveProcess.start()
            curr_move = minmaxQueue.get()
            minmaxQueue.empty()
            moveProcess.join()
            print(curr_move)
            board.pop()
            try:
                if curr_move > MATE_THRESHOLD:
                    curr_move -= 1
                elif curr_move < -MATE_THRESHOLD:
                    curr_move += 1
                best_move = min(
                    best_move,
                    curr_move,
                )
            except TypeError:
                minmaxQueue.put(0.0)
            beta = min(beta, best_move)
            if beta <= alpha:
                minmaxQueue.put(best_move)
        minmaxQueue.put(0.0)


talk()