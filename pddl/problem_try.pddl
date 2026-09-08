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

    (= (human_e) -1.77)

    (= (human_p) 0.57)

    (= (human_a) 1.8)

    (= (robot_e_sq) 11.8336)

    (= (robot_p_sq) 8.5849)

    (= (robot_a_sq) 0.8464)

    (= (human_e_sq) 3.1329)

    (= (human_p_sq) 0.3249)

    (= (human_a_sq) 3.24)

    (= (alpha) 1)

    (= (beta) 1)

    (= (gamma) 1)

    (= (total-cost) 0)

    (= (difficulty_limit) 1)

    (= (right_answers) 1)

    (= (wrong_answers) 0)

    (= (n_questions) 1)

    (= (n_easy) 3)

    (= (n_medium) 0)

    (= (n_hard) 3)

    (= (ask_uses) 1)

    (= (image_uses) 0)

    (= (sound_uses) 0)

    (= (mime_uses) 0)

    (= (category_limit) 1)

    (= (category_limit_bonus) 2)

    (= (ask_coeff) 1)

    (= (mime_coeff) 40)

    (= (sound_coeff) 60)

    (= (image_coeff) 20)

    (= (sound_easy_coeff) 1)

    (= (sound_medium_coeff) 1.1)

    (= (sound_hard_coeff) 1.2)

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
