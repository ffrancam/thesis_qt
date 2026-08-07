(define (problem task)
(:domain qt_quiz_domain)
(:objects
)
(:init
    (interaction_started)


    (quiz_introduced)




    (answered_wrong)

    (= (robot_e) 3.44)

    (= (robot_p) 2.93)

    (= (robot_a) 0.92)

    (= (human_e) 3.44)

    (= (human_p) 2.93)

    (= (human_a) 0.92)

    (= (robot_e_sq) 11.8336)

    (= (robot_p_sq) 8.5849)

    (= (robot_a_sq) 0.8464)

    (= (human_e_sq) 11.8336)

    (= (human_p_sq) 8.5849)

    (= (human_a_sq) 0.8464)

    (= (alpha) 1)

    (= (beta) 1)

    (= (gamma) 1)

    (= (total-cost) 0)

    (= (difficulty) 2)

    (= (right_answers) 1)

    (= (wrong_answers) 2)

    (= (n_questions) 3)

    (= (ask_coeff) 1111)

    (= (mime_coeff) 1111.2)

    (= (sound_coeff) 1.5)

    (= (image_coeff) 111.3)

    (= (sound_easy_coeff) 111)

    (= (sound_medium_coeff) 111)

    (= (sound_hard_coeff) 111)

    (= (image_easy_coeff) 11111)

    (= (image_medium_coeff) 111)

    (= (image_hard_coeff) 111)

    (= (ask_easy_coeff) 111)

    (= (ask_medium_coeff) 111)

    (= (ask_hard_coeff) 111)

    (= (mime_easy_coeff) 111)

)
(:goal (and
    (interaction_finished)
))

(:metric minimize (total-cost))
)
