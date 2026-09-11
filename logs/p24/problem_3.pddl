(define (problem task)
(:domain qt_quiz_domain_1)
(:objects
)
(:init
    (interaction_started)


    (quiz_introduced)



    (answered_wrong)

    (= (total-cost) 0)

    (= (difficulty_limit) 1)

    (= (right_answers) 2)

    (= (wrong_answers) 3)

    (= (n_questions) 5)

    (= (n_easy) 2)

    (= (n_medium) 2)

    (= (n_hard) 1)

    (= (ask_uses) 2)

    (= (image_uses) 1)

    (= (sound_uses) 1)

    (= (mime_uses) 1)

    (= (category_limit) 1)

    (= (category_limit_bonus) 2)

    (= (ask_coeff) 1)

    (= (mime_coeff) 20)

    (= (sound_coeff) 60)

    (= (image_coeff) 40)

    (= (sound_easy_coeff) 1)

    (= (sound_medium_coeff) 1)

    (= (sound_hard_coeff) 1)

    (= (image_easy_coeff) 1)

    (= (image_medium_coeff) 1)

    (= (image_hard_coeff) 1)

    (= (ask_easy_coeff) 1)

    (= (ask_medium_coeff) 1)

    (= (ask_hard_coeff) 1)

    (= (mime_easy_coeff) 1)

)
(:goal (and
    (interaction_finished)
))
)
