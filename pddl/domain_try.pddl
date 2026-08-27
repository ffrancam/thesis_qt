(define (domain qt_quiz_domain_1)
    (:requirements :strips :typing :fluents :action-costs :disjunctive-preconditions :negative-preconditions)

    (:predicates
        (interaction_started)
        (interaction_finished)

        (quiz_introduced)
        (quiz_finished)

        (can_conversate)
        (answered_wrong)
    )

    (:functions
        (total-cost)

        (difficulty_limit)
        (right_answers)
        (wrong_answers)

        (n_questions)
        (n_easy)
        (n_medium)
        (n_hard)

        (ask_uses)
        (image_uses)
        (sound_uses)
        (mime_uses)
        (category_limit)
        (category_limit_bonus)

        (ask_coeff)
        (mime_coeff)
        (sound_coeff)
        (image_coeff)

        (sound_easy_coeff)
        (sound_medium_coeff)
        (sound_hard_coeff)
        (image_easy_coeff)
        (image_medium_coeff)
        (image_hard_coeff)
        (ask_easy_coeff)
        (ask_medium_coeff)
        (ask_hard_coeff)
        (mime_easy_coeff)
    )


    (:action greet_warmly
        :parameters ()
        :precondition (not (interaction_started))
        :effect (interaction_started)
    )

    (:action say_goodbye
        :parameters ()
        :precondition (and
            (interaction_started)
            (quiz_finished)
        )
        :effect (and
            (not (interaction_started))
            (interaction_finished)
        )
    )

    (:action introduce_game
        :parameters ()
        :precondition (and
            (interaction_started)
            (not (quiz_introduced))
        )
        :effect (quiz_introduced)
    )

    (:action conclude_game
        :parameters ()
        :precondition (and
            (interaction_started)
            (quiz_introduced)
            (= (n_questions) 4)
        )
        :effect (and
            (not (quiz_introduced))
            (quiz_finished)
        )
    )


    ;; QUESTION RELATED ACTIONS

    ;; EASY

    (:action sound_easy
        :parameters ()
        :precondition (and
            (interaction_started)
            (quiz_introduced)
            (< (sound_uses) (category_limit))
            (<= (n_easy) (difficulty_limit))
            (not (can_conversate))
            (not (answered_wrong))
        )
        :effect (and
            (increase (total-cost) (+ (sound_coeff) (sound_easy_coeff)))
            (increase (n_questions) 1)
            (increase (n_easy) 1)
            (increase (sound_uses) 1)
        )
    )

    (:action image_easy
        :parameters ()
        :precondition (and
            (interaction_started)
            (quiz_introduced)
            (< (image_uses) (category_limit))
            (<= (n_easy) (difficulty_limit))
            (not (can_conversate))
            (not (answered_wrong))
        )
        :effect (and
            (increase (total-cost) (+ (image_coeff) (image_easy_coeff)))
            (increase (n_questions) 1)
            (increase (n_easy) 1)
            (increase (image_uses) 1)
        )
    )

    (:action ask_easy
        :parameters ()
        :precondition (and
            (interaction_started)
            (quiz_introduced)
            (< (ask_uses) (category_limit_bonus))
            (<= (n_easy) (difficulty_limit))
            (not (can_conversate))
            (not (answered_wrong))
        )
        :effect (and
            (increase (total-cost) (+ (ask_coeff) (ask_easy_coeff)))
            (increase (n_questions) 1)
            (increase (n_easy) 1)
            (increase (ask_uses) 1)
        )
    )

    (:action mime_easy
        :parameters ()
        :precondition (and
            (interaction_started)
            (quiz_introduced)
            (< (mime_uses) (category_limit))
            (<= (n_easy) (difficulty_limit))
            (not (can_conversate))
            (not (answered_wrong))
        )
        :effect (and
            (increase (total-cost) (+ (mime_coeff) (mime_easy_coeff)))
            (increase (n_questions) 1)
            (increase (n_easy) 1)
            (increase (mime_uses) 1)
        )
    )


    ;; MEDIUM

    (:action sound_medium
        :parameters ()
        :precondition (and
            (interaction_started)
            (quiz_introduced)
            (< (sound_uses) (category_limit))
            (> (n_easy) (difficulty_limit))
            (<= (n_medium) (difficulty_limit))
            (not (can_conversate))
            (not (answered_wrong))
        )
        :effect (and
            (increase (total-cost) (+ (sound_coeff) (sound_medium_coeff)))
            (increase (n_questions) 1)
            (increase (n_medium) 1)
            (increase (sound_uses) 1)
        )
    )

    (:action image_medium
        :parameters ()
        :precondition (and
            (interaction_started)
            (quiz_introduced)
            (< (image_uses) (category_limit))
            (> (n_easy) (difficulty_limit))
            (<= (n_medium) (difficulty_limit))
            (not (can_conversate))
            (not (answered_wrong))
        )
        :effect (and
            (increase (total-cost) (+ (image_coeff) (image_medium_coeff)))
            (increase (n_questions) 1)
            (increase (n_medium) 1)
            (increase (image_uses) 1)
        )
    )

    (:action ask_medium
        :parameters ()
        :precondition (and
            (interaction_started)
            (quiz_introduced)
            (< (ask_uses) (category_limit_bonus))
            (> (n_easy) (difficulty_limit))
            (<= (n_medium) (difficulty_limit))
            (not (can_conversate))
            (not (answered_wrong))
        )
        :effect (and
            (increase (total-cost) (+ (ask_coeff) (ask_medium_coeff)))
            (increase (n_questions) 1)
            (increase (n_medium) 1)
            (increase (ask_uses) 1)
        )
    )


    ;; HARD

    (:action sound_hard
        :parameters ()
        :precondition (and
            (interaction_started)
            (quiz_introduced)
            (< (sound_uses) (category_limit))
            (> (n_easy) (difficulty_limit))
            (> (n_medium) (difficulty_limit))
        )
        :effect (and
            (increase (total-cost) (+ (sound_coeff) (sound_hard_coeff)))
            (increase (n_questions) 1)
            (increase (n_hard) 1)
            (increase (sound_uses) 1)
        )
    )

    (:action image_hard
        :parameters ()
        :precondition (and
            (interaction_started)
            (quiz_introduced)
            (< (image_uses) (category_limit))
            (> (n_easy) (difficulty_limit))
            (> (n_medium) (difficulty_limit))
            (not (can_conversate))
            (not (answered_wrong))
        )
        :effect (and
            (increase (total-cost) (+ (image_coeff) (image_hard_coeff)))
            (increase (n_questions) 1)
            (increase (n_hard) 1)
            (increase (image_uses) 1)
        )
    )

    (:action ask_hard
        :parameters ()
        :precondition (and
            (interaction_started)
            (quiz_introduced)
            (< (ask_uses) (category_limit_bonus))
            (> (n_easy) (difficulty_limit))
            (> (n_medium) (difficulty_limit))
            (not (can_conversate))
            (not (answered_wrong))
        )
        :effect (and
            (increase (total-cost) (+ (ask_coeff) (ask_hard_coeff)))
            (increase (n_questions) 1)
            (increase (n_hard) 1)
            (increase (ask_uses) 1)
        )
    )

    (:action conversate
        :parameters ()
        :precondition (and
            (interaction_started)
            (quiz_introduced)
            (can_conversate)
        )
        :effect (and
            (not (can_conversate))
        )  
    )

    (:action comfort
        :parameters ()
        :precondition (and 
            (quiz_introduced)
            (answered_wrong)
        )
        :effect (and
            (not (answered_wrong))
        )
    )

)
