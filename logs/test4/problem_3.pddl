(define (problem task)
(:domain qt_quiz_domain_1)
(:objects
)
(:init
    (interaction_started)


    (quiz_introduced)


    (emotion_checked)



    (= (robot_e) 3.44)

    (= (robot_p) 2.93)

    (= (robot_a) 0.92)

    (= (human_e) -2.37)

    (= (human_p) -1.04)

    (= (human_a) -0.71)

    (= (robot_e_sq) 11.8336)

    (= (robot_p_sq) 8.5849)

    (= (robot_a_sq) 0.8464)

    (= (human_e_sq) 5.6169)

    (= (human_p_sq) 1.0816)

    (= (human_a_sq) 0.5041)

    (= (alpha) 1)

    (= (beta) 1)

    (= (gamma) 1)

    (= (total-cost) 0)

    (= (difficulty_limit) 1)

    (= (right_answers) 2)

    (= (wrong_answers) 1)

    (= (n_questions) 3)

    (= (n_easy) 3)

    (= (n_medium) 2)

    (= (n_hard) 4)

    (= (ask_uses) 1)

    (= (image_uses) 1)

    (= (sound_uses) 1)

    (= (mime_uses) 0)

    (= (category_limit) 1)

    (= (category_limit_bonus) 2)

    (= (ask_coeff) 20)

    (= (mime_coeff) 1)

    (= (sound_coeff) 60)

    (= (image_coeff) 40)

    (= (sound_easy_coeff) 10)

    (= (sound_medium_coeff) 11)

    (= (sound_hard_coeff) 12)

    (= (image_easy_coeff) 1)

    (= (image_medium_coeff) 1.1)

    (= (image_hard_coeff) 1.2)

    (= (ask_easy_coeff) 1)

    (= (ask_medium_coeff) 1.1)

    (= (ask_hard_coeff) 1.2)

    (= (mime_easy_coeff) 1)

)
(:goal (and
    (interaction_finished)
))

(:metric minimize (total-cost))
)
