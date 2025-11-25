"""
https://github.com/open-spaced-repetition/py-fsrs/blob/main/fsrs/fsrs.py
"""

from __future__ import annotations
import math
from datetime import datetime, timezone, timedelta

from utils.config import DEFAULT_PARAMETERS, DECAY, FACTOR, \
    State, Rating


def _short_term_stability(stability: float, rating: Rating) -> float:
    return stability * (
        math.e ** (DEFAULT_PARAMETERS[17] * (rating - 3 + DEFAULT_PARAMETERS[18]))
    )

def _next_difficulty(difficulty: float, rating: Rating) -> float:
    def _linear_damping(delta_difficulty: float, difficulty: float) -> float:
        return (10.0 - difficulty) * delta_difficulty / 9.0

    def _mean_reversion(arg_1: float, arg_2: float) -> float:
        return DEFAULT_PARAMETERS[7] * arg_1 + (1 - DEFAULT_PARAMETERS[7]) * arg_2

    arg_1 = difficulty
    delta_difficulty = -(DEFAULT_PARAMETERS[6] * (rating - 3))
    arg_2 = difficulty + _linear_damping(
        delta_difficulty=delta_difficulty, difficulty=difficulty
    )

    next_difficulty = _mean_reversion(arg_1=arg_1, arg_2=arg_2)

    # bound next_difficulty between 1 and 10
    next_difficulty = min(max(next_difficulty, 1.0), 10.0)

    return next_difficulty

def _next_interval(desired_retention: float, maximum_interval: int, stability: float) -> int:
    next_interval = (stability / FACTOR) * (
        (desired_retention ** (1 / DECAY)) - 1
    )

    next_interval = round(float(next_interval))  # intervals are full days

    # must be at least 1 day long
    next_interval = max(next_interval, 1)

    # can not be longer than the maximum interval
    next_interval = min(next_interval, maximum_interval)

    return next_interval

def _next_stability(difficulty: float, stability: float, retrievability: float, rating: Rating) -> float:
    if rating == Rating.Again:
        next_stability = _next_forget_stability(
            difficulty=difficulty,
            stability=stability,
            retrievability=retrievability,
        )

    elif rating in (Rating.Hard, Rating.Good, Rating.Easy):
        next_stability = _next_recall_stability(
            difficulty=difficulty,
            stability=stability,
            retrievability=retrievability,
            rating=rating,
        )

    return next_stability

def get_retrievability(stability: float, current_datetime: datetime | None, last_review: datetime | None) -> float:

    if last_review is None:
        return 0

    if current_datetime is None:
        current_datetime = datetime.now(timezone.utc)

    elapsed_days = max(0, (current_datetime - last_review).days)

    return (1 + FACTOR * elapsed_days / stability) ** DECAY

def _next_forget_stability(difficulty: float, stability: float, retrievability: float) -> float:
    next_forget_stability_long_term_params = (
        DEFAULT_PARAMETERS[11]
        * (difficulty ** -DEFAULT_PARAMETERS[12])
        * (((stability + 1) ** (DEFAULT_PARAMETERS[13])) - 1)
        * (math.e ** ((1 - retrievability) * DEFAULT_PARAMETERS[14]))
    )

    next_forget_stability_short_term_params = stability / (
        math.e ** (DEFAULT_PARAMETERS[17] * DEFAULT_PARAMETERS[18])
    )

    return min(
        next_forget_stability_long_term_params,
        next_forget_stability_short_term_params,
    )

def _next_recall_stability(difficulty: float, stability: float, retrievability: float, rating: Rating) -> float:
    hard_penalty = DEFAULT_PARAMETERS[15] if rating == Rating.Hard else 1
    easy_bonus = DEFAULT_PARAMETERS[16] if rating == Rating.Easy else 1

    return stability * (
        1
        + (math.e ** (DEFAULT_PARAMETERS[8]))
        * (11 - difficulty)
        * (stability ** -DEFAULT_PARAMETERS[9])
        * ((math.e ** ((1 - retrievability) * DEFAULT_PARAMETERS[10])) - 1)
        * hard_penalty
        * easy_bonus
    )


def learning_scheduler(
    state,
    stability,
    difficulty,
    rating,
    days_since_last_review,
    review_datetime,
    last_review,
    step,
    desired_retention = 0.9,
    learning_steps = (timedelta(minutes=1), timedelta(minutes=10)),
    re_learning_steps = (timedelta(minutes=10)),
    maximum_interval = 36500
):

    if review_datetime is None:
        review_datetime = datetime.now(timezone.utc)

    if last_review is None:
        last_review = review_datetime
        
    if days_since_last_review is None:
        days_since_last_review = (review_datetime - last_review).days

    if state == State.Learning:
        # update the card's stability and difficulty
        if  days_since_last_review is not None and days_since_last_review < 1:
            stability = _short_term_stability(
                stability=stability, rating=rating
            )
            difficulty = _next_difficulty(
                difficulty= difficulty,
                rating=rating
            )

        else:
            stability = _next_stability(
                difficulty=difficulty,
                stability=stability,
                retrievability= get_retrievability(
                    current_datetime=review_datetime,
                    last_review=last_review,
                    stability=stability
                ),
                rating=rating,
            )
            difficulty = _next_difficulty(
                difficulty=difficulty, rating=rating
            )

        step = 0 if step is None else step
        
        # calcular el siguiente intervalo de la tarjeta
        ## la primera cláusula if se ocupa del caso en que la tarjeta en estado de aprendizaje estaba previamente
        ## programada con un Programador con más pasos_de_aprendizaje que el Programador actual
        if (step >= len(learning_steps) and 
            rating in (Rating.Hard, Rating.Good, Rating.Easy)
            ):
            state = State.Review
            step = None

            next_interval_days = _next_interval(stability=stability, maximum_interval=maximum_interval, desired_retention=desired_retention)
            next_interval = timedelta(days=next_interval_days)

        else:
            if rating == Rating.Again:
                step = 0
                next_interval = learning_steps[step]

            elif rating == Rating.Hard:
                # card step stays the same

                if step == 0 and len(learning_steps) == 1:
                    next_interval = learning_steps[0] * 1.5
                elif step == 0 and len(learning_steps) >= 2:
                    next_interval = (
                        learning_steps[0] + learning_steps[1]
                    ) / 2.0
                else:
                    next_interval = learning_steps[step]

            elif rating == Rating.Good:
                if step + 1 == len(learning_steps):  # the last step
                    state = State.Review
                    step = None

                    next_interval_days = _next_interval(stability=stability, maximum_interval=maximum_interval, desired_retention=desired_retention)
                    next_interval = timedelta(days=next_interval_days)

                else:
                    step += 1
                    next_interval = learning_steps[step]

            elif rating == Rating.Easy:
                state = State.Review
                step = None

                next_interval_days = _next_interval(stability=stability, maximum_interval=maximum_interval, desired_retention=desired_retention)
                next_interval = timedelta(days=next_interval_days)

    elif state == State.Review:
        # update the card's stability and difficulty
        if days_since_last_review is not None and days_since_last_review < 1:
            stability = _short_term_stability(
                stability=stability, rating=rating
            )
            difficulty = _next_difficulty(
                difficulty=difficulty, rating=rating
            )

        else:
            stability = _next_stability(
                difficulty=difficulty,
                stability=stability,
                retrievability=get_retrievability(
                    current_datetime=review_datetime
                ),
                rating=rating,
            )
            difficulty = _next_difficulty(
                difficulty=difficulty,
                rating=rating
            )

        # calculate the card's next interval
        if rating == Rating.Again:
            # if there are no relearning steps (they were left blank)
            if len(re_learning_steps) == 0:
                next_interval_days = _next_interval(stability=stability, maximum_interval=maximum_interval, desired_retention=desired_retention)
                next_interval = timedelta(days=next_interval_days)

            else:
                state = State.Relearning
                step = 0

                next_interval = re_learning_steps[step]

        elif rating in (Rating.Hard, Rating.Good, Rating.Easy):
            next_interval_days = _next_interval(stability=stability, maximum_interval=maximum_interval, desired_retention=desired_retention)
            next_interval = timedelta(days=next_interval_days)

    elif state == State.Relearning:
        # update the card's stability and difficulty
        if days_since_last_review is not None and days_since_last_review < 1:
            stability = _short_term_stability(
                stability=stability, rating=rating
            )
            difficulty = _next_difficulty(
                difficulty=difficulty, rating=rating
            )

        else:
            stability = _next_stability(
                difficulty=difficulty,
                stability=stability,
                retrievability= get_retrievability(
                    current_datetime=review_datetime
                ),
                rating=rating,
            )
            difficulty = _next_difficulty(
                difficulty=difficulty, rating=rating
            )

        # calculate the card's next interval
        ## first if-clause handles edge case where the Card in the Relearning state was previously
        ## scheduled with a Scheduler with more relearning_steps than the current Scheduler
        if (step >= len(re_learning_steps)
            and rating in (Rating.Hard, Rating.Good, Rating.Easy)
        ):
            state = State.Review
            step = None

            next_interval_days = _next_interval(stability=stability, maximum_interval=maximum_interval, desired_retention=desired_retention)
            next_interval = timedelta(days=next_interval_days)

        else:
            if rating == Rating.Again:
                step = 0
                next_interval = re_learning_steps[step]

            elif rating == Rating.Hard:
                # card step stays the same

                if step == 0 and len(re_learning_steps) == 1:
                    next_interval = re_learning_steps[0] * 1.5
                elif step == 0 and len(re_learning_steps) >= 2:
                    next_interval = (
                        re_learning_steps[0] + re_learning_steps[1]
                    ) / 2.0
                else:
                    next_interval = re_learning_steps[step]

            elif rating == Rating.Good:
                if step + 1 == len(re_learning_steps):  # the last step
                    state = State.Review
                    step = None

                    next_interval_days = _next_interval(stability=stability, maximum_interval=maximum_interval, desired_retention=desired_retention)
                    next_interval = timedelta(days=next_interval_days)

                else:
                    step += 1
                    next_interval = re_learning_steps[step]

            elif rating == Rating.Easy:
                state = State.Review
                step = None

                next_interval_days = _next_interval(stability=stability, maximum_interval=maximum_interval, desired_retention=desired_retention)
                next_interval = timedelta(days=next_interval_days)


    due = review_datetime + next_interval
    last_review = review_datetime

    return last_review, review_datetime, days_since_last_review, due, stability, difficulty, state, rating, step