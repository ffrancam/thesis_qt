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

    (= (human_e) -2.29)

    (= (human_p) -1.44)

    (= (human_a) -2.04)

    (= (robot_e_sq) 11.8336)

    (= (robot_p_sq) 8.5849)

    (= (robot_a_sq) 0.8464)

    (= (human_e_sq) 5.2441)

    (= (human_p_sq) 2.0736)

    (= (human_a_sq) 4.1616)

    (= (alpha) 1)

    (= (beta) 1)

    (= (gamma) 1)

    (= (total-cost) 0)

    (= (difficulty_limit) 1)

    (= (right_answers) 4)

    (= (wrong_answers) 0)

    (= (n_questions) 4)

    (= (n_easy) 2)

    (= (n_medium) 2)

    (= (n_hard) 0)

    (= (ask_uses) 1)

    (= (image_uses) 1)

    (= (sound_uses) 1)

    (= (mime_uses) 1)

    (= (category_limit) 1)

    (= (category_limit_bonus) 2)

    (= (ask_coeff) 60)

    (= (mime_coeff) 1)

    (= (sound_coeff) 20)

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
