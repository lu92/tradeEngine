import uuid
from collections import namedtuple
from enum import Enum, auto
from typing import Callable


class PriceChangedEvent:
    def __init__(self, ticker: str, price: float) -> None:
        self.ticker = ticker
        self.price = price


class Place:
    def __init__(self, ticker: str):
        self.id = uuid.uuid1()
        self.ticker = ticker
        self.currentPrice = 0.0

    def __str__(self):
        return 'Place [id: {}, ticker: {}, currentPrice: {}]'.format(self.id, self.ticker, self.currentPrice)


class Action:
    def __init__(self, fun: Callable[[], None]) -> None:
        self.fun = fun

    def invoke(self):
        self.fun()


class Transition:
    def __init__(self, action: Action):
        self.id = uuid.uuid1()
        self.action = action

    def trigger(self):
        print("Transition {} will be invoked!".format(self.id))
        self.action.invoke()
        print("Transition {} has finished!".format(self.id))


ConditionType = namedtuple('ConditionType', ['value', 'displayString'])


class ConditionTypes(Enum):

    @property
    def displayString(self):
        return self.value.displayString

    GT = ConditionType(1, 'Greater Than')
    GE = ConditionType(2, 'Greater Than Or Equal')
    LT = ConditionType(3, 'Less Than')
    LE = ConditionType(4, 'Less Than Or Equal')


class Condition:

    def __init__(self, ticker: str, type: ConditionType, predicate: Callable[[float], bool]) -> None:
        self.ticker = ticker
        self.predicate = predicate
        self.type = type

    def check(self, price: float) -> bool:
        outcome = (self.predicate)(price)
        print('Condition: [{} {} {}]: {}'.format(self.ticker, self.type.displayString, price, outcome))
        return outcome

    @staticmethod
    def greaterThan(ticker: str, value: float):
        predicate: Callable[[float], bool] = lambda price: price > value
        return Condition(ticker, ConditionTypes.GT, predicate)

    @staticmethod
    def greaterThanOrEqual(ticker: str, value: float):
        predicate: Callable[[float], bool] = lambda price: price >= value
        return Condition(ticker, ConditionTypes.GE, predicate)

    @staticmethod
    def lessThan(ticker: str, value: float):
        predicate: Callable[[float], bool] = lambda price: price < value
        return Condition(ticker, ConditionTypes.LT, predicate)

    @staticmethod
    def lessThanOrEqual(ticker: str, value: float):
        predicate: Callable[[float], bool] = lambda price: price <= value
        return Condition(ticker, ConditionTypes.LE, predicate)


class InArc:
    def __init__(self, place: Place, condition: Condition, transition: Transition):
        self.place = place
        self.condition = condition
        self.transition = transition


class OutArc:
    def __init__(self, transition: Transition, place: Place):
        self.transition = transition
        self.place = place


class PetriNet:

    def __init__(self, data: dict) -> None:
        self.data = data

    def find_arc_for_ticker(self, ticker: str) -> InArc:
        return next(filter(lambda arc: arc.place.ticker == ticker, self.data['inArcs']), None)

    def update_price_of_ticker(self, place: Place, new_price: float):
        place.currentPrice = new_price

    def findTransitions(self, ticker: str) -> [Transition]:
        return list(map(lambda founded: founded.transition,
                        filter(lambda arc: arc.place.ticker == ticker, self.data['inArcs'])))

    def isReady(self, transition: Transition) -> bool:
        print('Considered transaction: {}'.format(transition.id))
        arcs = list(filter(lambda arc: arc.transition == transition, self.data['inArcs']))
        is_ready = all(arc.condition.check(arc.place.currentPrice) for arc in arcs)
        print("Transaction {} is ready: {}\n".format(transition.id, is_ready))
        return is_ready

    def findReadyTransitions(self, event: PriceChangedEvent) -> [Transition]:
        return list(filter(lambda transition: self.isReady(transition), self.findTransitions(event.ticker)))

    def accept(self, event: PriceChangedEvent):
        arc = self.find_arc_for_ticker(event.ticker)
        self.update_price_of_ticker(arc.place, event.price)
        self.triggerReadyTransitions(event)

    def triggerReadyTransitions(self, event: PriceChangedEvent):
        ready_transitions = self.findReadyTransitions(event)
        for readyTransition in ready_transitions:
            readyTransition.trigger()


if __name__ == '__main__':
    place1 = Place("BTCUSDT")
    place2 = Place("GNTBTC")
    place3 = Place("ETHBTC")
    end_place = Place("Rule executed")

    transition = Transition(Action(lambda: print("XXX")))
    transition2 = Transition(Action(lambda: print("YYY")))

    places = [place1, place2, place3]
    transitions = [transition, transition2]

    inArcs = [InArc(place1, Condition.greaterThan('BTCUSDT', 15000), transition),
              InArc(place2, Condition.greaterThan("GNTBTC", 0.2), transition),
              InArc(place3, Condition.greaterThanOrEqual('ETHBTC', 0.3), transition2)]
    outArcs = [OutArc(transition, end_place),
               OutArc(transition2, end_place)]

    petri_net = PetriNet({
        'places': places,
        'transitions': transitions,
        'inArcs': inArcs,
        'outArcs': outArcs
    })

    petri_net.accept(PriceChangedEvent("BTCUSDT", 16000))
    petri_net.accept(PriceChangedEvent("ETHBTC", 0.3))
