# Dependencies
import copy
import math
import config
from time import time
import numpy as np
from node import Node
from chess_handler import ChessStateHandler
from state import StateHandler
import random
from neural_network import NeuralNet
import torch
from game_data import GameData
import sys


def monte_carlo_tree_search(root: Node, state_handler: StateHandler, sigma: float, policy: NeuralNet =None, max_itr=0, max_time=0) -> Node:
    """
    Runs the monte carlo tree search algorithm.
    If max_itr is 0, it will run until max_time is reached, else it will run for max_itr iterations.
    Returns the root node of the tree generated with the given root.
    """
    if max_itr == 0:
        start_time = time.time()
        while time.time() - start_time < max_time:
            chosen_node: Node = selection(root)
            created_node: Node = expansion(chosen_node, state_handler)
            result: int = simulation(created_node, policy) # TODO ADD SIGMA TO SIMULATION
            backpropagation(created_node, result)
    else:
        itr = 0
        while itr < max_itr:
            chosen_node: Node = selection(root)
            created_node = expansion(chosen_node, state_handler)
            result = simulation(created_node, policy)
            backpropagation(created_node, result)
            itr += 1

    return root


def selection(node: Node) -> Node:
    '''
    This selects the best leaf for expansion.
    For Monte Carlo this is the node that you should expand.
    Given by exploration and exploitation means.
    '''
    child_nodes = node.get_children()
    best_child = None
    best_node_value = 0

    while child_nodes:
        for child_node in child_nodes:
            if (best_node_value < ucb(child_node)):
                best_child = child_node
                best_node_value = ucb(child_node)
        return selection(best_child)
    return node


def expansion(node: Node, state_handler: StateHandler) -> Node:
    """
    Generates a new child to node. It is generated by making a random move, 
    checking if that move has a corresponding child, if not it generates a child with the random move.
    Repeats until a child is generated
    """
    moves = state_handler.get_legal_actions()
    for move in moves:
        # virtual_state_handler = state_handler.move_to_state()
        state_handler.step(move)

        child_node = Node(copy.deepcopy(state_handler))
        node.add_child(child_node)
        state_handler.step_back()
    # TODO: Make use of default policy
    if node.get_children():
        return random.choice(node.get_children())
    else:
        return node


def choose_move(game: StateHandler, policy: NeuralNet=None):
    """"
    Chooses a move for the given game. If a policy is given, it will use the policy to choose a move, else it will choose a random move.
    """
    if policy is not None:
        move = policy.default_policy(game)
    else:    
        legal_actions = game.get_legal_actions()
        # print("THE INDEX: " +str(len(legal_actions)-1))
        index = random.randint(0, len(legal_actions)-1)
        move = legal_actions[index]
    return move


def simulation(node: Node, policy: NeuralNet=None) -> int:
    """
    In this process, a simulation is performed by choosing moves or strategies until a result or predefined state is achieved.
    """
    state = copy.deepcopy(node.get_state())
    while not state.is_finished():
        state.step(choose_move(state, policy))  # TODO refactor

    return state.get_winner()

# GPT-4 MADNESS
# def simulation(node: Node, sigma: float, critic: NeuralNet=None) -> int:
#     """
#     In this process, a simulation is performed by choosing moves or strategies until a result or predefined state is achieved.
#     """
#     state = copy.deepcopy(node.get_state())

#     while not state.is_finished():
#         state.step(choose_move(state))  # TODO refactor

#     if random.random() < sigma:
#         return state.get_winner()
#     else:
#         estimated_value = critic.predict(state.get_board_state())  # assuming the critic's predict function returns the estimated value of the input state
#         return estimated_value


def backpropagation(node: Node, result: int) -> None:
    """
    After determining the value of the newly added node, the remaining tree must be updated. 
    So, the backpropagation process is performed, where it backpropagates from the new node to the root node. 
    During the process, the number of simulation stored in each node is incremented. Also, if the new node’s 
    simulation results in a win, then the number of wins is also incremented.
    """
    node.add_visits()
    node.add_reward(result)
    if not node.has_parent():  # if node is not root, then it has a parent and backpropagates to it
        backpropagation(node.get_parent(), -result)

def ucb(node: Node):
    """
    Takes in node and returns upper confidence bound based on parent node visits and node visits
    """
    visits = node.get_visits()
    parent_visits = node.get_parent().get_visits()
    if visits == 0:
        visits = 1
    if parent_visits == 0:
        parent_visits = 1

    exploration_parameter = math.sqrt(2)
    exploitation = node.get_wins()/visits
    exploration = np.sqrt(np.log(parent_visits/visits))
    return exploitation + exploration_parameter*exploration

def softmax(list: list) -> list:
    """
    Takes in a list and returns a list with softmax applied to it
    """
    exp_list = np.exp(list)
    sum_exp_list = np.sum(exp_list)
    result = exp_list/sum_exp_list
    return result

def get_action_probabilities(node: Node) -> list:
    """
    Finds the best move to be done by Monte Carlo by Node.
    Should return a vector containing all move probabilities.
    """
    distributions = []
    #Append simulations
    # TODO: CHECK FOR CORRECT CHILDREN, send children and probability as a pair
    # Check if we need to add wins over visits, while appending children

    i = 0
    # print(node.get_state().get_actions_mask())
    for action in node.get_state().get_actions_mask():
        #
        #
        if (action == 1):
            # legals = np.where(node.get_state().get_actions_mask()==1)
            # print(len(legals[0]))
            # print(len(node.get_children()))
            # print(i)
            distributions.append(node.get_children()[i].get_visits())
            i += 1
        else:
            distributions.append(-100)

    # Softmax of result
    distributions = softmax(distributions)
    
    return distributions
    
def get_best_action(node: Node) -> Node:
    """
    Finds the best move to be done by Monte Carlo by Node.
    Function returning best move (as a node) based on number of simulations performed.
    """
    # Check if game is finished
    if node.get_state().is_finished():
        return node
    
    max_visits = -1
    best_node: Node = None
    child: Node
    for child in node.get_children():
        if child.get_visits() > max_visits:
            max_visits = child.get_visits()
            best_node = child
    return best_node

def generate_test_data(start_node: Node, num_games: int, sims_pr_game: int, model: NeuralNet = None):
    """
    Generates test data for the neural network
    """
    #state = node.get_state().get_board_state()
    # start_node = start_node
    
    for game_iteration in range(num_games):
        GameData.clear_data_file()
        root = Node(start_node.get_state())
        game: StateHandler = root.get_state()
        # game = StateHandler() # Initialize the actual game board (B_a) to an empty board
        print("Iteration: " + str(game_iteration))
        game.render()
        print("")
        while not game.is_finished() and root != None:
            monte_carlo_tree_search(root, game, config.SIGMA, model, sims_pr_game) 
            player = game.get_current_player()

            state = root.get_state().get_board_state()
            # Add the player to the start point of state
            state = np.insert(state, 0, player)
            # print("Player in state: " + str(player))

            distribution = get_action_probabilities(root)
            distribution = np.asarray(distribution, dtype=np.float32)
            # print("state: " + str(state) + " distribution: " + str(distribution))
            GameData.add_data(state, distribution)
            
            # Choose actual move (a*) based on distribution
            best_move_root: Node = get_best_action(root)
            root = best_move_root
            game = root.get_state()
            game.render()
            print("")


if __name__ == "__main__":
    sys.setrecursionlimit(5000)
    # game = ChessStateHandler()
    # node = Node(game.get_state())

    # expanded_node = expansion(node, game)
    # print("Amount of children: ", len(node.get_children()))
    # for child in node.get_children():
    #     print("=====================================")
    #     print(child.get_state())
    # print("=====================================")
    # print(expanded_node.get_state())
    
    print("Test generate test data:")
    print(sys.getrecursionlimit())
    chessHandler = ChessStateHandler()

    # Create a Neural Network
    model = NeuralNet(config.INPUT_SIZE, config.HIDDEN_SIZE, config.OUTPUT_SIZE)
    
    # create root node
    root = Node(chessHandler)
    
    generate_test_data(root, config.MCTS_GAMES, config.MCTS_SIMULATIONS)
