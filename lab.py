"""6.009 Lab 9: Carlae Interpreter Part 2"""

import sys
sys.setrecursionlimit(10_000)

# KEEP THE ABOVE LINES INTACT, BUT REPLACE THIS COMMENT WITH YOUR lab.py FROM
# THE PREVIOUS LAB, WHICH SHOULD BE THE STARTING POINT FOR THIS LAB.
#!/usr/bin/env python3
"""6.009 Lab 8: Carlae (LISP) Interpreter"""

import doctest

# NO ADDITIONAL IMPORTS!


###########################
# Carlae-related Exceptions #
###########################


class CarlaeError(Exception):
    """
    A type of exception to be raised if there is an error with a Carlae
    program.  Should never be raised directly; rather, subclasses should be
    raised.
    """

    pass


class CarlaeSyntaxError(CarlaeError):
    """
    Exception to be raised when trying to evaluate a malformed expression.
    """

    pass


class CarlaeNameError(CarlaeError):
    """
    Exception to be raised when looking up a name that has not been defined.
    """

    pass


class CarlaeEvaluationError(CarlaeError):
    """
    Exception to be raised if there is an error during evaluation other than a
    CarlaeNameError.
    """

    pass


############################
# Tokenization and Parsing #
############################


def number_or_symbol(x):
    """
    Helper function: given a string, convert it to an integer or a float if
    possible; otherwise, return the string itself

    >>> number_or_symbol('8')
    8
    >>> number_or_symbol('-5.32')
    -5.32
    >>> number_or_symbol('1.2.3.4')
    '1.2.3.4'
    >>> number_or_symbol('x')
    'x'
    """
    try:
        return int(x)
    except ValueError:
        try:
            return float(x)
        except ValueError:
            return x


def tokenize(source):
    """
    Splits an input string into meaningful tokens (left parens, right parens,
    other whitespace-separated values).  Returns a list of strings.

    Arguments:
        source (str): a string containing the source code of a Carlae
                      expression
    """
    output = []
    # keep track of whether a current line being read is a comment
    is_comment = False
    current_token = []
    
    for i in range(len(source)):
        if is_comment:
            # going to new line, so comment ends
            if source[i] == '\n':
                is_comment = False
        else:
            if source[i] == '(':
                output.append(source[i])
            elif source[i] == ')':
                # if there was a multiple-character token
                # add it to output, and reset current token list
                if len(current_token) != 0:
                    output.append(''.join(current_token))
                    current_token = []
                output.append(source[i])
            # comment reached. Ignore rest of line
            elif source[i] == '#':
                is_comment = True
            # if whitespace, and there was a multiple-character 
            # token being parsed, then add it to output and reset current token list
            elif source[i].isspace():
                if len(current_token) != 0:
                    output.append(''.join(current_token))
                    current_token = []
            # if it's not whitespace, then it's part of current multiple-character token
            else:
                current_token.append(source[i])
    # get final multiple character token, if necessary
    if len(current_token) != 0:
        output.append(''.join(current_token))
    
    return output

def parse(tokens):
    """
    Parses a list of tokens, constructing a representation where:
        * symbols are represented as Python strings
        * numbers are represented as Python ints or floats
        * S-expressions are represented as Python lists

    Arguments:
        tokens (list): a list of strings representing tokens
    (:= circle-area (function (r) (* 3.14 (* r r))))

    [':=', 'circle-area', ['function', ['r'], ['*', 3.14, ['*', 'r', 'r']]]]
    """
    # will keep track of all S-expressions. The last one is the most nested S-expression
    lists = []
    # keep track of how many '(' there are to see if parenthesis are mismatched
    open_parens = 0

    for token in tokens:
        # new S-expression
        if token == '(':
            open_parens += 1
            lists.append([])
        # current S-expression ended
        elif token == ')':
            # if mismatched parenthesis, raise exception
            if open_parens <= 0:
                raise CarlaeSyntaxError()
            # if this current S-expression is nested, delete it from lists, nest it into
            # the S-expression located in the index before it in lists, and update
            # the number of open parenthesis
            elif len(lists) >= 2:
                lists[-2].append(lists[-1])
                del lists[-1]
                open_parens -= 1
            # if it isn't nested, then just update the number of open parenthesis
            else:
                open_parens -= 1
        # if it's not a parenthesis, then its a atomic expression, so if there's a current S-expression
        # being parsed, add it to that. Otherwise, it's isolated. Either case, add it lists
        elif open_parens >= 1:
            lists[-1].append(number_or_symbol(token))
        else:
            # isolated atomic expressions. There can't be more than one isolated atomic
            # expression, so if there is, raise a syntax error
            if len(lists) >= 1 and not isinstance(lists[-1], list):
                raise CarlaeSyntaxError()
            lists.append(number_or_symbol(token))
    # if mismatched parenthesis, raise syntax error
    if open_parens != 0:
        raise CarlaeSyntaxError()
    # return the outermost S-expression
    return lists[0] 

######################
# Built-in Functions #
######################

class Pair():
    """
    Then nodes of singly linked lists that represent Carlae lists
    """
    def __init__(self, pair):
        # if wrong number of arguments given, raise error
        if len(pair) != 2:
            raise CarlaeEvaluationError
        self.head = pair[0]
        self.tail = pair[1]
        
class Environment():

    def __init__(self, parent = None):
        # assign pointer to parent environment
        self.parent = parent
        # create empty dictionary for variable assignments that take place
        # in the environment
        self.assignment = dict()

    def lookup(self, var):
        # if var is not a string, raise exception
        if not isinstance(var, str):
            raise CarlaeEvaluationError()
        # recursive look up for parent assignment
        elif var in self.assignment:
            return self.assignment[var]
        # if this environment has no parent, no more environemnts
        # can be checked, so variable doesn't exist so raise exception
        elif self.parent == None:
            raise CarlaeNameError()
        else:
            # if not found here, check the parent environment
            return self.parent.lookup(var)
        
    def set_var(self, var, val):
        # if var is not a string, raise exception
        if not isinstance(var, str):
            raise CarlaeEvaluationError()
        # recursive look up for parent assignment
        elif var in self.assignment:
            self.assignment[var] = val
            return val
        # if this environment has no parent, no more environemnts
        # can be checked, so variable doesn't exist so raise exception
        elif self.parent == None:
            raise CarlaeNameError()
        else:
            # if not found here, check the parent environment
            return self.parent.set_var(var, val)

class User_Def_Functions(object):
    """
    Class for user defined functions. Takes in the parameters of the function,
    the actual operations (or definition) of the function, and the environment it was created in.
    """
    def __init__(self, param, func, environment):
        self.variables = param
        self.function = func
        self.env = environment

    def __call__(self, args):
        # create new environment upon call
        new_env = Environment(self.env)
        # if not enough arguments, raise exception
        if len(self.variables) != len(args):
            raise CarlaeEvaluationError()

        # assign all variables to corresponding input arguments
        for v in range(len(self.variables)):
            new_env.assignment[self.variables[v]] = args[v]
        return evaluate(self.function, new_env)

def result_and_env(tree, environment=None):
    # create environment if none 
    if environment == None:
        parent = Environment()
        parent.assignment = carlae_builtins
        environment = Environment(parent)
    return evaluate(tree, environment), environment


def get_item_from_pair(args, item):
    """
    Returns an item from a given pair. Expects Args to be a list containing the given
    pair and the item parameter is what your looking for, so either the head or the tail
    of the pair
    """
    # check if wrong number of arguments given and if arguments passed in are correct type
    if len(args) == 1 and isinstance(args[0], Pair):
        # if so, return whichever item was asked for
        return args[0].head if item == 'head' else args[0].tail
    raise CarlaeEvaluationError

def product(tree):
    """
    Product function for carlea builtin * function.
    """
    # Special Cases:
    # if no arguments are given and only if one argument is given
    if len(tree) == 0:
        return 1
    elif len(tree) == 1:
        return tree[0]
    # otherwise, multiply all numbers together and return product
    prod = tree[0]
    for val in tree[1:]:
        prod *= val
    return prod

def division(tree):
    """
    Division function for carlea builtin / function
    """
    # Special cases:
    # if no divisor was given, and if only one argument was given
    if len(tree) == 0:
        raise ValueError
    elif len(tree) == 1:
        return 1/tree[0]
    # otherwise, divide the first number by the rest of the numbers
    # and return result
    quotient = tree[0]
    for val in tree[1:]:
        quotient /= val
    return quotient

"""
Built-In Functions for conditional operators
    =? should evaluate to true if all of its arguments are equal to each other.
    > should evaluate to true if its arguments are in decreasing order.
    >= should evaluate to true if its arguments are in nonincreasing order.
    < should evaluate to true if its arguments are in increasing order.
    <= should evaluate to true if its arguments are in nondecreasing order.
"""
def all_equal(args):
    arg = evaluate(args[0]) 
    for i in range(1, len(args)):
        if evaluate(args[i-1]) != evaluate(args[i]):
            return False
    return True

def decreasing(args):
    for i in range(1, len(args)):
        if not args[i-1] > args[i]:
            return False
    return True

def nonincreasing(args):
    for i in range(1, len(args)):
        if not args[i-1] >= args[i]:
            return False
    return True

def increasing(args):
    for i in range(1, len(args)):
        if not args[i-1] < args[i]:
            return False
    return True

def nondecreasing(args):
    for i in range(1, len(args)):
        if not args[i-1] <= args[i]:
            return False
    return True

def and_func(args):
    for arg in args:
        if not evaluate(arg):
            return False
    return True

def or_func(args):
    for arg in args:
        if evaluate(arg):
            return True
    return False

def not_func(args):
    if len(args) != 1:
        raise CarlaeEvaluationError
    return not args[0]

def linked_list(args):
    """
    Creates linked list given the items that will be stored
    """
    # return empty list
    if len(args) == 0:
        return None
    # otherwise, get the inner-most nested pair and iteratively
    # build the list
    current_pair = Pair([args[-1], None])
    for i in range(-2, -len(args)-1, -1):
        current_pair = Pair([args[i], current_pair])
    return current_pair

def is_list(args):
    """
    Checks if given arguments is a linked list. Returns boolean
    """
    # check if empty list
    if args[0] == None:
        return True
    # check if linked list
    l = args[0]
    if isinstance(l, Pair):
        # go through whole list
        while l.tail != None:
            # check if any item is not a pair
            if not isinstance(l.tail, Pair): 
                return False
            l = l.tail
        return True
    return False

def get_length(args):
    """
    Given a linked list, returns the its length
    """
    # if not given a linked list, raise exception
    if not is_list([args[0]]):
        raise CarlaeEvaluationError
    # if empty list, return 0
    if args[0] == None:
        return 0
    # otherwise, guaranteed length of at least 1
    length = 1
    # get linked list from args list and iteratively go through it
    # keep track of how many pairs make it up
    l = args[0]
    while l.tail != None:
        length += 1
        l = l.tail
    return length

def index(args):
    """
    Returns the item at index i given a linked list
    """
    # separate arguments: the linked list and index i
    clist, i = args
    # if linked list empty, raise an exception
    if clist == None:
        raise CarlaeEvaluationError
    # if a solo pair and index equal 0, return the pairs head
    elif not is_list([clist]) and isinstance(clist, Pair):
        if i == 0:
            return clist.head
        # otherwise, raise exception
        raise CarlaeEvaluationError
    # iteratively traverse linked list until we reach index i
    curr_item = clist
    for curr_i in range(1, i+1):
        curr_item = curr_item.tail
        # have reached end of linked list
        if curr_item == None:
            raise CarlaeEvaluationError
    # return item at index i
    return curr_item.head

def copy(clist):
    """
    Given linked list, returns a copy of it
    """
    # if list empty, return empty list
    if clist == None:
        return None
    # if not give linked list, raise exception
    elif not isinstance(clist, Pair):
        raise CarlaeEvaluationError
    # otherwise, recursively create copy of linked list
    elif clist.tail == None:
        return Pair([clist.head, None])
    return Pair([clist.head, copy(clist.tail)])

def concat(clists):
    """
    Given a list of linked lists, returns the concatenated list of all given lists
    """
    # if no lists given, return empty linked list
    if len(clists) == 0:
        return None
    # if only one linked list given, return a copy of it
    elif len(clists) == 1 and is_list([clists[0]]):
        # create new list 
        return copy(clists[0])
    # if not given linked list, raise error
    if not is_list([clists[0]]):
        raise CarlaeEvaluationError
    # otherwise, find the first non empty linked list
    ind = 0
    # if none given, return empty linked list
    while ind < len(clists):
        # create copy of current linked list
        cclist = copy(clists[ind])
        if cclist != None: # stop when not empty
            break
        ind += 1
    flist = cclist
    # for every other remaining linked list
    for i in range(ind+1, len(clists)):
        # if it's not a linked list, raise error
        if not is_list([clists[i]]):
            raise CarlaeEvaluationError
        # if empty, no need to concatenate
        elif clists[i] == None:
            continue
        # otherwise, make copy of it 
        clist = copy(clists[i])
        # iteratively get to the end of the current concatenated list
        # add the current linked list
        while cclist.tail != None:
            cclist = cclist.tail
        cclist.tail = clist
    # returning pointer to head of concatenated linked list
    return flist

def map_func(args):
    # if wrong number of args given, raise error
    if len(args) != 2:
        raise CarlaeEvaluationError
    # otherwise, separate args
    function, original_list = args
    # create copy of list given
    clist = copy(original_list)
    # is emtpy, return another empty list
    if clist == None:
        return None
    output = clist
    # traverse through copy of linked list
    while clist.tail != None:
        # apply function to every item in linked list
        clist.head = function([clist.head])
        clist = clist.tail
    # run function on element of list
    clist.head = function([clist.head])
    # return pointer of head of linked list
    return output

def filter_func(args):
    # if wrong number of args given, raise error
    if len(args) != 2:
        raise CarlaeEvaluationError
    # if emtpy list, return another empty list
    elif args[1] == None:
        return None
    # otherwise, separate args
    function, og_list = args

    def helper_func(c_pair):
        #Base Case: current_pair is the last pair of the list
        if c_pair.tail == None: 
            if function([c_pair.head]):
                return Pair([c_pair.head, None])
            return None
        #Recursive Case: there are more pairs in the list after current_pair
        if function([c_pair.head]):
            return Pair([c_pair.head, helper_func(c_pair.tail)])
        return helper_func(c_pair.tail) #skip the current pair head

    return helper_func(og_list)

def reduce_func(args):
    # if wrong number of args given, raise error
    if len(args) != 3:
        raise CarlaeEvaluationError
    # if empty list given, return the init value
    elif args[1] == None:
        return args[2]
    # otherwise, separate argumetns
    func, clist, numb = args
    # iterate through linked list
    while clist.tail != None:
        # pass on init value and current item of linked list to function
        # and reassign to init value
        numb = func([numb, clist.head])
        clist = clist.tail
    numb = func([numb, clist.head])

    return numb

def begin(args):
    # return the final argument of given evaluated statements
    return args[-1]

carlae_builtins = {
    "+": sum,
    "-": lambda args: -args[0] if len(args) == 1 else (args[0] - sum(args[1:])),
    "*": lambda args: product(args),
    "/": lambda args: division(args),
    '@t': True,
    '@f': False,
    'nil': None,
    '=?': all_equal,
    '>': decreasing,
    '>=': nonincreasing,
    '<': increasing,
    '<=': nondecreasing,
    'and': and_func,
    'or': or_func,
    'not': not_func,
    'pair': lambda args: Pair(args),
    'head': lambda arg: get_item_from_pair(arg, 'head'),
    'tail': lambda arg: get_item_from_pair(arg, 'tail'),
    'list': linked_list,
    'list?': is_list,
    'length': get_length,
    'nth': index,
    'concat':concat,
    'map': map_func,
    'filter': filter_func,
    'reduce': reduce_func,
    'begin': begin
}

##############
# Evaluation #
##############


def evaluate(tree, environment = None):
    """
    Evaluate the given syntax tree according to the rules of the Carlae
    language.

    Arguments:
        tree (type varies): a fully parsed expression, as the output from the
                            parse function
    """
    if environment == None:
        # create new environment, where the parent is the global frame
        # that has the built-in functions
        parent = Environment()
        parent.assignment = carlae_builtins
        environment = Environment(parent)
    # if dealing with number, simply return it
    if isinstance(tree, (int, float)):
        return tree
    # if dealing with variable, look it up recursively
    elif isinstance(tree, str):
        return environment.lookup(tree)
    elif isinstance(tree, list):
        # dealing with S-expression
        # if empty list, raise evaluation error
        if tree == None:
            return None
        elif len(tree) == 0:
            raise CarlaeEvaluationError()
        # if assigning a new variable
        elif tree[0] == ':=':
            # if the second item in S-expression is a list, it's the easier function
            # definition, so write it as a normal function definition, evaluate it,
            # assign to the variable name given and also return it
            if isinstance(tree[1], list):
                var_name = tree[1][0]
                if len(tree[1]) > 1:
                    args = tree[1][1:]
                else:
                    args = []
                func_def = ['function', args, tree[2]]
                value = evaluate(func_def, environment)
                environment.assignment[var_name] = value
                return value
            # otherwise, simply dealing with a normal variable
            # so just assign it in the given environment and return it
            value = evaluate(tree[2], environment)
            environment.assignment[tree[1]] = evaluate(tree[2], environment)
            return value 
        # if we're defining a new function...
        elif tree[0] == "function":
            # create a new user defined function object and return it
            return User_Def_Functions(tree[1], tree[2], environment)
        elif tree[0] == 'if':
            # check if condition given is true or false
            if evaluate(tree[1], environment):
                return evaluate(tree[2], environment)
            else:
                return evaluate(tree[3], environment)
        elif tree[0] == 'nil': # empty list
            return None
        elif tree[0] == 'del':
            if tree[1] in environment.assignment:
                return environment.assignment.pop(tree[1])
            else:
                raise CarlaeNameError
        elif tree[0] == 'let':
            assignments = {}
            for assignment in tree[1]:
                assignments[assignment[0]] = evaluate(assignment[1], environment)
            env = Environment(environment)
            env.assignment = assignments
            return evaluate(tree[2], env)
        elif tree[0] == 'set!':
            return environment.set_var(tree[1], evaluate(tree[2], environment))

        # if the first item in the tree is yet another list, we're dealing with
        # an in-line defined function
        elif isinstance(tree[0], list):
            # like the lambda function in Python
            lambda_func = evaluate(tree[0], environment)
            # evaluate each argument and return function call
            args = [evaluate(arg, environment) for arg in tree[1:]]
            return lambda_func(args)
        else:
            # last possible S-expression is function call, which we attempt to
            # look up, then evaluate all arguments and return the function call
            func = environment.lookup(tree[0])
            if tree[0] in ('and', 'or'):
                args = (evaluate(arg, environment) for arg in tree[1:])
            else:
                args = [evaluate(arg, environment) for arg in tree[1:]]
            return func(args)
    return environment.lookup(tree)

def evaluate_file(file_name, env = None):
    file = open(file_name, 'r')
    line = file.read().splitlines()
    return evaluate(parse(tokenize(" ".join(line))))

def REPL(environment=None):
    user_input = input("in> ")
    if environment == None:
        parent = Environment()
        parent.assignment = carlae_builtins
        environment = Environment(parent)
        
    while user_input != "EXIT":
        tokens = tokenize(user_input)
        parsed = parse(tokens)

        # raise error and continue
        try:
            result, env = result_and_env(parsed, environment)
            print ("out> "+str(result))
        except:
            print ("EvaluationError")
        user_input = input("in> ")

if __name__ == "__main__":
    # code in this block will only be executed if lab.py is the main file being
    # run (not when this module is imported)

    # uncommenting the following line will run doctests from above
    # doctest.testmod()

    files = sys.argv[1:]
    env = None
    if len(files) > 0:
        parent = Environment()
        parent.assignment = carlae_builtins
        env = Environment(parent)
        for file in files:
            evaluate_file(file, parent)
    
    REPL(env)
