#!/usr/bin/env python3
# pylos.py
# Author: Quentin Lurkin
# Version: April 28, 2017
# -*- coding: utf-8 -*-

import argparse
import json

from lib import game


class PylosState(game.GameState):
    """Class representing a state for the Pylos game."""

    def __init__(self, initialstate=None):

        if initialstate is None:
            # define a layer of the board
            def squareMatrix(size):
                matrix = []
                for i in range(size):
                    matrix.append([None] * size)
                return matrix

            board = []
            for i in range(4):
                board.append(squareMatrix(4 - i))

            initialstate = {
                'board': board,
                'reserve': [15, 15],
                'turn': 0
            }

        super().__init__(initialstate)

    def get(self, layer, row, column):
        if layer < 0 or row < 0 or column < 0:
            raise game.InvalidMoveException('The position ({}) is outside of the board'.format([layer, row, column]))
        try:
            return self._state['visible']['board'][layer][row][column]
        except:
            raise game.InvalidMoveException('The position ({}) is outside of the board'.format([layer, row, column]))

    def safeGet(self, layer, row, column):
        try:
            return self.get(layer, row, column)
        except game.InvalidMoveException:
            return None

    def validPosition(self, layer, row, column):
        if self.get(layer, row, column) is not None:
            raise game.InvalidMoveException('The position ({}) is not free'.format([layer, row, column]))

        if layer > 0:
            if (
                                    self.get(layer - 1, row, column) is None or
                                    self.get(layer - 1, row + 1, column) is None or
                                self.get(layer - 1, row + 1, column + 1) is None or
                            self.get(layer - 1, row, column + 1) is None
            ):
                raise game.InvalidMoveException('The position ({}) is not stable'.format([layer, row, column]))

    def canMove(self, layer, row, column):
        if self.get(layer, row, column) is None:
            raise game.InvalidMoveException('The position ({}) is empty'.format([layer, row, column]))

        if layer < 3:
            if (
                                    self.safeGet(layer + 1, row, column) is not None or
                                    self.safeGet(layer + 1, row - 1, column) is not None or
                                self.safeGet(layer + 1, row - 1, column - 1) is not None or
                            self.safeGet(layer + 1, row, column - 1) is not None
            ):
                raise game.InvalidMoveException('The position ({}) is not movable'.format([layer, row, column]))

    def createSquare(self, coord):
        layer, row, column = tuple(coord)

        def isSquare(layer, row, column):
            if (
                                    self.safeGet(layer, row, column) is not None and
                                    self.safeGet(layer, row + 1, column) == self.safeGet(layer, row, column) and
                                self.safeGet(layer, row + 1, column + 1) == self.safeGet(layer, row, column) and
                            self.safeGet(layer, row, column + 1) == self.safeGet(layer, row, column)
            ):
                return True
            return False

        if (
                            isSquare(layer, row, column) or
                            isSquare(layer, row - 1, column) or
                        isSquare(layer, row - 1, column - 1) or
                    isSquare(layer, row, column - 1)
        ):
            return True
        return False

    def set(self, coord, value):
        layer, row, column = tuple(coord)
        self.validPosition(layer, row, column)
        self._state['visible']['board'][layer][row][column] = value

    def remove(self, coord, player):
        layer, row, column = tuple(coord)
        self.canMove(layer, row, column)
        sphere = self.get(layer, row, column)
        if sphere != player:
            raise game.InvalidMoveException('not your sphere')
        self._state['visible']['board'][layer][row][column] = None

    # update the state with the move
    # raise game.InvalidMoveException
    def update(self, move, player):
        state = self._state['visible']
        if move['move'] == 'place':
            if state['reserve'][player] < 1:
                raise game.InvalidMoveException('no more sphere')
            self.set(move['to'], player)
            state['reserve'][player] -= 1
        elif move['move'] == 'move':
            if move['to'][0] <= move['from'][0]:
                raise game.InvalidMoveException('you can only move to upper layer')
            sphere = self.remove(move['from'], player)
            try:
                self.set(move['to'], player)
            except game.InvalidMoveException as e:
                self.set(move['from'], player)
                raise e
        else:
            raise game.InvalidMoveException('Invalid Move:\n{}'.format(move))

        if 'remove' in move:
            if not self.createSquare(move['to']):
                raise game.InvalidMoveException('You cannot remove spheres')
            if len(move['remove']) > 2:
                raise game.InvalidMoveException('Can\'t remove more than 2 spheres')
            for coord in move['remove']:
                sphere = self.remove(coord, player)
                state['reserve'][player] += 1

        state['turn'] = (state['turn'] + 1) % 2

    # return 0 or 1 if a winner, return None if draw, return -1 if game continue
    def winner(self):
        state = self._state['visible']
        if state['reserve'][0] < 1:
            return 1
        elif state['reserve'][1] < 1:
            return 0
        return -1

    def val2str(self, val):
        return '_' if val == None else '@' if val == 0 else 'O'

    def player2str(self, val):
        return 'Light' if val == 0 else 'Dark'

    def printSquare(self, matrix):
        print(' ' + '_' * (len(matrix) * 2 - 1))
        print('\n'.join(map(lambda row: '|' + '|'.join(map(self.val2str, row)) + '|', matrix)))

    # print the state
    def prettyprint(self):
        state = self._state['visible']
        for layer in range(4):
            self.printSquare(state['board'][layer])
            print()

        for player, reserve in enumerate(state['reserve']):
            print('Reserve of {}:'.format(self.player2str(player)))
            print((self.val2str(player) + ' ') * reserve)
            print()

        print('{} to play !'.format(self.player2str(state['turn'])))
        # print(json.dumps(self._state['visible'], indent=4))


class PylosServer(game.GameServer):
    """Class representing a server for the Pylos game."""

    def __init__(self, verbose=False):
        super().__init__('Pylos', 2, PylosState(), verbose=verbose)

    def applymove(self, move):
        try:
            self._state.update(json.loads(move), self.currentplayer)
        except json.JSONDecodeError:
            raise game.InvalidMoveException('move must be valid JSON string: {}'.format(move))


class PylosClient(game.GameClient):
    """Class representing a client for the Pylos game."""

    def __init__(self, name, server, verbose=False):
        super().__init__(server, PylosState, verbose=verbose)
        self.__name = name

    def cancelupdate(self, state, move, player):
        st = state._state['visible']
        st['turn'] = (st['turn'] + 1) % 2
        if move['move'] == 'place':
            state.remove(move['to'], player)
            st['reserve'][player] += 1
        elif move['move'] == 'move':
            sphere = state.remove(move['to'], player)
            state.set(move['from'], player)

        if 'remove' in move:
            for coord in move['remove']:
                sphere = state.set(coord, player)
                st['reserve'][player] -= 1

    def wayup(self, state, player, layer):
        layer += 1
        while layer <= 3:
            for row in range(4 - layer):
                for column in range(4 - layer):
                    try:
                        move = {'move': 'place', 'to': [layer, row, column]}
                        state.update(move, player)
                        self.cancelupdate(state, move, player)
                        return {'wayup': True, 'pos': move}
                    except game.InvalidMoveException:
                        pass
            layer += 1
        return {'wayup': False, 'pos': None}

    def _handle(self, message):
        pass

    # return move as string
    def _nextmove(self, state):
        player = state._state['visible']['turn']
        noplayer = (player + 1) % 2
        move = dict()
        move['move'] = str(input('Place or Move?: '))
        if move['move'] == 'place':
            layer = int(input('Etage: '))
            row = int(input('Ligne: '))
            column =int(input('Collonne: '))
            move['to'] = [layer, row, column]
        elif move['move'] == 'move':
            print('De')
            layer = int(input('Etage: '))
            row = int(input('Ligne: '))
            column = int(input('Collonne: '))
            move['from'] = [layer, row, column]
            print('Vers')
            layer = int(input('Etage: '))
            row = int(input('Ligne: '))
            column = int(input('Collonne: '))
            move['to'] = [layer, row, column]
        state.update(move, player)
        if state.createSquare(move['to']):
            move['remove'] = []
            retir = int(input('Combien de bille a retirer? '))
            while len(move['remove']) < retir:
                layer = int(input('Etage: '))
                row = int(input('Ligne: '))
                column = int(input('Collonne: '))
                move['remove'].append([layer, row, column])
        return json.dumps(move)

if __name__ == '__main__':
    # Create the top-level parser
    parser = argparse.ArgumentParser(description='Pylos game')
    subparsers = parser.add_subparsers(description='server client', help='Pylos game components', dest='component')
    # Create the parser for the 'server' subcommand
    server_parser = subparsers.add_parser('server', help='launch a server')
    server_parser.add_argument('--host', help='hostname (default: localhost)', default='localhost')
    server_parser.add_argument('--port', help='port to listen on (default: 5000)', default=5000)
    server_parser.add_argument('--verbose', action='store_true')
    # Create the parser for the 'client' subcommand
    client_parser = subparsers.add_parser('client', help='launch a client')
    client_parser.add_argument('name', help='name of the player')
    client_parser.add_argument('--host', help='hostname of the server (default: localhost)', default='127.0.0.1')
    client_parser.add_argument('--port', help='port of the server (default: 5000)', default=5000)
    client_parser.add_argument('--verbose', action='store_true')
    # Parse the arguments of sys.args
    args = parser.parse_args()
    if args.component == 'server':
        PylosServer(verbose=args.verbose).run()
    else:
        PylosClient(args.name, (args.host, args.port), verbose=args.verbose)
