(define (domain qt_quiz_domain_1)
    (:requirements :strips :typing :fluents :action-costs :disjunctive-preconditions :negative-preconditions)

    (:predicates
        (interaction_started)
        (interaction_finished)

        (quiz_introduced)
        (quiz_finished)

        (emotion_checked)

        (can_conversate)
        (answered_wrong)
    )

    (:functions
        (robot_e)
        (robot_p)
        (robot_a)
        (human_e)
        (human_p)
        (human_a)

        (robot_e_sq)
        (robot_p_sq)
        (robot_a_sq)
        (human_e_sq)
        (human_p_sq)
        (human_a_sq)

        (alpha)
        (beta)
        (gamma)
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


    (:action check_emotion
        :parameters ()
        :precondition (not (emotion_checked))
        :effect (emotion_checked)
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
        :effect (and 
            (quiz_introduced)
            (not (emotion_checked))
         )
    )

    (:action conclude_game
        :parameters ()
        :precondition (and 
            (interaction_started)
            (quiz_introduced)
            (= (n_questions) 5)
            ;(= (human_e) 3.44)
        )
        :effect (and 
            (not (quiz_introduced))
            (quiz_finished)
        )
    )


    (:action conversate
        :parameters ()
        :precondition (and
            (interaction_started)
            (quiz_introduced)
            (emotion_checked)
            (can_conversate)
            (>= (human_e) 0.0)
            (>= (robot_e) 0.0)
        )
        :effect (and
            (increase (total-cost)
                (* 0.0
                    (+ (* 0.0
                            (+ (+ (robot_e_sq) (+ (* -6.88 (robot_e)) 11.8336))
                                (+ (+ (robot_p_sq) (+ (* -5.86 (robot_p)) 8.5849))
                                (+ (robot_a_sq) (+ (* -1.84 (robot_a)) 0.8464)))))
                        (+ (* 0.0
                                (+ (+ (human_e_sq) (+ (* -6.88 (human_e)) 11.8336))
                                    (+ (+ (human_p_sq) (+ (* -5.86 (human_p)) 8.5849))
                                    (+ (human_a_sq) (+ (* -1.84 (human_a)) 0.8464)))))
                            (+ (* 0.0
                                    (+ (+ (robot_e_sq) (+ (* -6.88 (robot_e)) 11.8336))
                                        (+ (+ (robot_p_sq) (+ (* -5.86 (robot_p)) 8.5849))
                                        (+ (robot_a_sq) (+ (* -1.84 (robot_a)) 0.8464)))))
                                (* 0.0
                                    (+ (+ (human_e_sq) (+ (* -6.88 (human_e)) 11.8336))
                                        (+ (+ (human_p_sq) (+ (* -5.86 (human_p)) 8.5849))
                                        (+ (human_a_sq) (+ (* -1.84 (human_a)) 0.8464))))))))))
            (not (emotion_checked))
            (not (can_conversate))
            (assign (robot_e) 3.44)
            (assign (robot_p) 2.93)
            (assign (robot_a) 0.92)
            (assign (robot_e_sq) 11.8336)
            (assign (robot_p_sq) 8.5849)
            (assign (robot_a_sq) 0.8464)
            (assign (human_e) 3.44)
            (assign (human_p) 2.93)
            (assign (human_a) 0.92)
            (assign (human_e_sq) 11.8336)
            (assign (human_p_sq) 8.5849)
            (assign (human_a_sq) 0.8464)
        )  
    )


    ;; QUESTION RELATED ACTIONS

    (:action sound_easy
        :parameters ()
        :precondition (and 
            (interaction_started)
            (quiz_introduced)
            (emotion_checked)
            (< (sound_uses) (category_limit))
            (<= (n_easy) (difficulty_limit))
            (>= (human_e) 0.0)
            (>= (robot_e) 0.0)
            (not (can_conversate))
            (not (answered_wrong))
        )
        :effect (and
            (increase (total-cost)
                (+ (sound_coeff)
                    (+ (sound_easy_coeff) (+ (* 1.0
                            (+ (+ (robot_e_sq) (+ (* -6.88 (robot_e)) 11.8336))
                                (+ (+ (robot_p_sq) (+ (* -5.86 (robot_p)) 8.5849))
                                (+ (robot_a_sq) (+ (* -1.84 (robot_a)) 0.8464)))))
                        (+ (* 1.0
                                (+ (+ (human_e_sq) (+ (* -6.88 (human_e)) 11.8336))
                                    (+ (+ (human_p_sq) (+ (* -5.86 (human_p)) 8.5849))
                                    (+ (human_a_sq) (+ (* -1.84 (human_a)) 0.8464)))))
                            (+ (* 1.0
                                    (+ (+ (robot_e_sq) (+ (* -6.88 (robot_e)) 11.8336))
                                        (+ (+ (robot_p_sq) (+ (* -5.86 (robot_p)) 8.5849))
                                        (+ (robot_a_sq) (+ (* -1.84 (robot_a)) 0.8464)))))
                                (* 1.0
                                    (+ (+ (human_e_sq) (+ (* -6.88 (human_e)) 11.8336))
                                        (+ (+ (human_p_sq) (+ (* -5.86 (human_p)) 8.5849))
                                        (+ (human_a_sq) (+ (* -1.84 (human_a)) 0.8464)))))))))))
            (not (emotion_checked))
            (increase (n_questions) 1)
            (increase (n_easy) 1)
            (assign (robot_e) 3.44)
            (assign (robot_p) 2.93)
            (assign (robot_a) 0.92)
            (assign (robot_e_sq) 11.8336)
            (assign (robot_p_sq) 8.5849)
            (assign (robot_a_sq) 0.8464)
            (assign (human_e) 3.44)
            (assign (human_p) 2.93)
            (assign (human_a) 0.92)
            (assign (human_e_sq) 11.8336)
            (assign (human_p_sq) 8.5849)
            (assign (human_a_sq) 0.8464)
            (increase (sound_uses) 1)
        )
    )
    
    (:action image_easy
        :parameters ()
        :precondition (and 
            (interaction_started)
            (quiz_introduced)
            (emotion_checked)
            (< (image_uses) (category_limit))
            (<= (n_easy) (difficulty_limit))
            (>= (human_e) 0.0)
            (>= (robot_e) 0.0)
            (not (can_conversate))
            (not (answered_wrong))
        )
        :effect (and 
            (increase (total-cost)
                (+ (image_coeff)
                    (+ (image_easy_coeff) (+ (* 1.0
                            (+ (+ (robot_e_sq) (+ (* -6.88 (robot_e)) 11.8336))
                                (+ (+ (robot_p_sq) (+ (* -5.86 (robot_p)) 8.5849))
                                (+ (robot_a_sq) (+ (* -1.84 (robot_a)) 0.8464)))))
                        (+ (* 1.0
                                (+ (+ (human_e_sq) (+ (* -6.88 (human_e)) 11.8336))
                                    (+ (+ (human_p_sq) (+ (* -5.86 (human_p)) 8.5849))
                                    (+ (human_a_sq) (+ (* -1.84 (human_a)) 0.8464)))))
                            (+ (* 1.0
                                    (+ (+ (robot_e_sq) (+ (* -6.88 (robot_e)) 11.8336))
                                        (+ (+ (robot_p_sq) (+ (* -5.86 (robot_p)) 8.5849))
                                        (+ (robot_a_sq) (+ (* -1.84 (robot_a)) 0.8464)))))
                                (* 1.0
                                    (+ (+ (human_e_sq) (+ (* -6.88 (human_e)) 11.8336))
                                        (+ (+ (human_p_sq) (+ (* -5.86 (human_p)) 8.5849))
                                        (+ (human_a_sq) (+ (* -1.84 (human_a)) 0.8464)))))))))))
            (not (emotion_checked))
            (increase (n_questions) 1)
            (increase (n_easy) 1)
            (assign (robot_e) 3.44)
            (assign (robot_p) 2.93)
            (assign (robot_a) 0.92)
            (assign (robot_e_sq) 11.8336)
            (assign (robot_p_sq) 8.5849)
            (assign (robot_a_sq) 0.8464)
            (assign (human_e) 3.44)
            (assign (human_p) 2.93)
            (assign (human_a) 0.92)
            (assign (human_e_sq) 11.8336)
            (assign (human_p_sq) 8.5849)
            (assign (human_a_sq) 0.8464)
            (increase (image_uses) 1)
        )
    )
    
    (:action ask_easy
        :parameters ()
        :precondition (and 
            (interaction_started)
            (quiz_introduced)
            (emotion_checked)
            (< (ask_uses) (category_limit_bonus))
            (<= (n_easy) (difficulty_limit))
            (>= (human_e) 0.0)
            (>= (robot_e) 0.0)
            (not (can_conversate))
            (not (answered_wrong))
        )
        :effect (and
            (increase (total-cost)
                (+ (ask_coeff)
                    (+ (ask_easy_coeff) (+ (* 1.0
                            (+ (+ (robot_e_sq) (+ (* -6.88 (robot_e)) 11.8336))
                                (+ (+ (robot_p_sq) (+ (* -5.86 (robot_p)) 8.5849))
                                (+ (robot_a_sq) (+ (* -1.84 (robot_a)) 0.8464)))))
                        (+ (* 1.0
                                (+ (+ (human_e_sq) (+ (* -6.88 (human_e)) 11.8336))
                                    (+ (+ (human_p_sq) (+ (* -5.86 (human_p)) 8.5849))
                                    (+ (human_a_sq) (+ (* -1.84 (human_a)) 0.8464)))))
                            (+ (* 1.0
                                    (+ (+ (robot_e_sq) (+ (* -6.88 (robot_e)) 11.8336))
                                        (+ (+ (robot_p_sq) (+ (* -5.86 (robot_p)) 8.5849))
                                        (+ (robot_a_sq) (+ (* -1.84 (robot_a)) 0.8464)))))
                                (* 1.0
                                    (+ (+ (human_e_sq) (+ (* -6.88 (human_e)) 11.8336))
                                        (+ (+ (human_p_sq) (+ (* -5.86 (human_p)) 8.5849))
                                        (+ (human_a_sq) (+ (* -1.84 (human_a)) 0.8464)))))))))))
            (not (emotion_checked))
            (increase (n_questions) 1)
            (increase (n_easy) 1)
            (assign (robot_e) 3.44)
            (assign (robot_p) 2.93)
            (assign (robot_a) 0.92)
            (assign (robot_e_sq) 11.8336)
            (assign (robot_p_sq) 8.5849)
            (assign (robot_a_sq) 0.8464)
            (assign (human_e) 3.44)
            (assign (human_p) 2.93)
            (assign (human_a) 0.92)
            (assign (human_e_sq) 11.8336)
            (assign (human_p_sq) 8.5849)
            (assign (human_a_sq) 0.8464)
            (increase (ask_uses) 1)
        )
    )
    
    (:action mime_easy
        :parameters ()
        :precondition (and 
            (interaction_started)
            (quiz_introduced)
            (emotion_checked)
            (< (mime_uses) (category_limit))
            (<= (n_easy) (difficulty_limit))
            (>= (human_e) 0.0)
            (>= (robot_e) 0.0)
            (not (can_conversate))
            (not (answered_wrong))
        )
        :effect (and 
            (increase (total-cost)
                (+ (mime_coeff)
                    (+ (mime_easy_coeff) (+ (* 1.0
                            (+ (+ (robot_e_sq) (+ (* -6.88 (robot_e)) 11.8336))
                                (+ (+ (robot_p_sq) (+ (* -5.86 (robot_p)) 8.5849))
                                (+ (robot_a_sq) (+ (* -1.84 (robot_a)) 0.8464)))))
                        (+ (* 1.0
                                (+ (+ (human_e_sq) (+ (* -6.88 (human_e)) 11.8336))
                                    (+ (+ (human_p_sq) (+ (* -5.86 (human_p)) 8.5849))
                                    (+ (human_a_sq) (+ (* -1.84 (human_a)) 0.8464)))))
                            (+ (* 1.0
                                    (+ (+ (robot_e_sq) (+ (* -6.88 (robot_e)) 11.8336))
                                        (+ (+ (robot_p_sq) (+ (* -5.86 (robot_p)) 8.5849))
                                        (+ (robot_a_sq) (+ (* -1.84 (robot_a)) 0.8464)))))
                                (* 1.0
                                    (+ (+ (human_e_sq) (+ (* -6.88 (human_e)) 11.8336))
                                        (+ (+ (human_p_sq) (+ (* -5.86 (human_p)) 8.5849))
                                        (+ (human_a_sq) (+ (* -1.84 (human_a)) 0.8464)))))))))))
            (not (emotion_checked))
            (increase (n_questions) 1)
            (increase (n_easy) 1)
            (assign (robot_e) 3.44)
            (assign (robot_p) 2.93)
            (assign (robot_a) 0.92)
            (assign (robot_e_sq) 11.8336)
            (assign (robot_p_sq) 8.5849)
            (assign (robot_a_sq) 0.8464)
            (assign (human_e) 3.44)
            (assign (human_p) 2.93)
            (assign (human_a) 0.92)
            (assign (human_e_sq) 11.8336)
            (assign (human_p_sq) 8.5849)
            (assign (human_a_sq) 0.8464)
            (increase (mime_uses) 1)
        )
    )
    
    
    
    ;; MEDIUM
    
    (:action sound_medium
        :parameters ()
        :precondition (and 
            (interaction_started)
            (quiz_introduced)
            (emotion_checked)
            (< (sound_uses) (category_limit))
            (> (n_easy) (difficulty_limit))
            (<= (n_medium) (difficulty_limit))
            (>= (human_e) 0.0)
            (>= (robot_e) 0.0)
            (not (can_conversate))
            (not (answered_wrong))
        )
        :effect (and
            (increase (total-cost)
                (+ (sound_coeff)
                    (+ (sound_medium_coeff) (+ (* 1.0
                            (+ (+ (robot_e_sq) (+ (* -6.88 (robot_e)) 11.8336))
                                (+ (+ (robot_p_sq) (+ (* -5.86 (robot_p)) 8.5849))
                                (+ (robot_a_sq) (+ (* -1.84 (robot_a)) 0.8464)))))
                        (+ (* 1.0
                                (+ (+ (human_e_sq) (+ (* -6.88 (human_e)) 11.8336))
                                    (+ (+ (human_p_sq) (+ (* -5.86 (human_p)) 8.5849))
                                    (+ (human_a_sq) (+ (* -1.84 (human_a)) 0.8464)))))
                            (+ (* 1.0
                                    (+ (+ (robot_e_sq) (+ (* -6.88 (robot_e)) 11.8336))
                                        (+ (+ (robot_p_sq) (+ (* -5.86 (robot_p)) 8.5849))
                                        (+ (robot_a_sq) (+ (* -1.84 (robot_a)) 0.8464)))))
                                (* 1.0
                                    (+ (+ (human_e_sq) (+ (* -6.88 (human_e)) 11.8336))
                                        (+ (+ (human_p_sq) (+ (* -5.86 (human_p)) 8.5849))
                                        (+ (human_a_sq) (+ (* -1.84 (human_a)) 0.8464)))))))))))
            (not (emotion_checked))
            (increase (n_questions) 1)
            (increase (n_medium) 1)
            (assign (robot_e) 3.44)
            (assign (robot_p) 2.93)
            (assign (robot_a) 0.92)
            (assign (robot_e_sq) 11.8336)
            (assign (robot_p_sq) 8.5849)
            (assign (robot_a_sq) 0.8464)
            (assign (human_e) 3.44)
            (assign (human_p) 2.93)
            (assign (human_a) 0.92)
            (assign (human_e_sq) 11.8336)
            (assign (human_p_sq) 8.5849)
            (assign (human_a_sq) 0.8464)
            (increase (sound_uses) 1)
        )
    )
    
    (:action image_medium
        :parameters ()
        :precondition (and 
            (interaction_started)
            (quiz_introduced)
            (emotion_checked)
            (< (image_uses) (category_limit))
            (> (n_easy) (difficulty_limit))
            (<= (n_medium) (difficulty_limit))
            (>= (human_e) 0.0)
            (>= (robot_e) 0.0)
            (not (can_conversate))
            (not (answered_wrong))
        )
        :effect (and 
            (increase (total-cost)
                (+ (image_coeff)
                    (+ (image_medium_coeff) (+ (* 1.0
                            (+ (+ (robot_e_sq) (+ (* -6.88 (robot_e)) 11.8336))
                                (+ (+ (robot_p_sq) (+ (* -5.86 (robot_p)) 8.5849))
                                (+ (robot_a_sq) (+ (* -1.84 (robot_a)) 0.8464)))))
                        (+ (* 1.0
                                (+ (+ (human_e_sq) (+ (* -6.88 (human_e)) 11.8336))
                                    (+ (+ (human_p_sq) (+ (* -5.86 (human_p)) 8.5849))
                                    (+ (human_a_sq) (+ (* -1.84 (human_a)) 0.8464)))))
                            (+ (* 1.0
                                    (+ (+ (robot_e_sq) (+ (* -6.88 (robot_e)) 11.8336))
                                        (+ (+ (robot_p_sq) (+ (* -5.86 (robot_p)) 8.5849))
                                        (+ (robot_a_sq) (+ (* -1.84 (robot_a)) 0.8464)))))
                                (* 1.0
                                    (+ (+ (human_e_sq) (+ (* -6.88 (human_e)) 11.8336))
                                        (+ (+ (human_p_sq) (+ (* -5.86 (human_p)) 8.5849))
                                        (+ (human_a_sq) (+ (* -1.84 (human_a)) 0.8464)))))))))))
            (not (emotion_checked))
            (increase (n_questions) 1)
            (increase (n_medium) 1)
            (assign (robot_e) 3.44)
            (assign (robot_p) 2.93)
            (assign (robot_a) 0.92)
            (assign (robot_e_sq) 11.8336)
            (assign (robot_p_sq) 8.5849)
            (assign (robot_a_sq) 0.8464)
            (assign (human_e) 3.44)
            (assign (human_p) 2.93)
            (assign (human_a) 0.92)
            (assign (human_e_sq) 11.8336)
            (assign (human_p_sq) 8.5849)
            (assign (human_a_sq) 0.8464)
            (increase (image_uses) 1)
        )
    )
    
    (:action ask_medium
        :parameters ()
        :precondition (and 
            (interaction_started)
            (quiz_introduced)
            (emotion_checked)
            (< (ask_uses) (category_limit_bonus))
            (> (n_easy) (difficulty_limit))
            (<= (n_medium) (difficulty_limit))
            (>= (human_e) 0.0)
            (>= (robot_e) 0.0)
            (not (can_conversate))
            (not (answered_wrong))
        )
        :effect (and
            (increase (total-cost)
                (+ (ask_coeff)
                    (+ (ask_medium_coeff) (+ (* 1.0
                            (+ (+ (robot_e_sq) (+ (* -6.88 (robot_e)) 11.8336))
                                (+ (+ (robot_p_sq) (+ (* -5.86 (robot_p)) 8.5849))
                                (+ (robot_a_sq) (+ (* -1.84 (robot_a)) 0.8464)))))
                        (+ (* 1.0
                                (+ (+ (human_e_sq) (+ (* -6.88 (human_e)) 11.8336))
                                    (+ (+ (human_p_sq) (+ (* -5.86 (human_p)) 8.5849))
                                    (+ (human_a_sq) (+ (* -1.84 (human_a)) 0.8464)))))
                            (+ (* 1.0
                                    (+ (+ (robot_e_sq) (+ (* -6.88 (robot_e)) 11.8336))
                                        (+ (+ (robot_p_sq) (+ (* -5.86 (robot_p)) 8.5849))
                                        (+ (robot_a_sq) (+ (* -1.84 (robot_a)) 0.8464)))))
                                (* 1.0
                                    (+ (+ (human_e_sq) (+ (* -6.88 (human_e)) 11.8336))
                                        (+ (+ (human_p_sq) (+ (* -5.86 (human_p)) 8.5849))
                                        (+ (human_a_sq) (+ (* -1.84 (human_a)) 0.8464)))))))))))
            (not (emotion_checked))
            (increase (n_questions) 1)
            (increase (n_medium) 1)
            (assign (robot_e) 3.44)
            (assign (robot_p) 2.93)
            (assign (robot_a) 0.92)
            (assign (robot_e_sq) 11.8336)
            (assign (robot_p_sq) 8.5849)
            (assign (robot_a_sq) 0.8464)
            (assign (human_e) 3.44)
            (assign (human_p) 2.93)
            (assign (human_a) 0.92)
            (assign (human_e_sq) 11.8336)
            (assign (human_p_sq) 8.5849)
            (assign (human_a_sq) 0.8464)
            (increase (ask_uses) 1)
        )
    )
    
    
    
    ;; HARD

    (:action sound_hard
        :parameters ()
        :precondition (and 
            (interaction_started)
            (quiz_introduced)
            (emotion_checked)
            (< (sound_uses) (category_limit))
            (> (n_easy) (difficulty_limit))
            (> (n_medium) (difficulty_limit))
            ;(<= (n_hard) (difficulty_limit))
            (>= (human_e) 0.0)
            (>= (robot_e) 0.0)
            (not (can_conversate))
            (not (answered_wrong))
        )
        :effect (and
            (increase (total-cost)
                (+ (sound_coeff)
                    (+ (sound_hard_coeff) (+ (* 1.0
                            (+ (+ (robot_e_sq) (+ (* -6.88 (robot_e)) 11.8336))
                                (+ (+ (robot_p_sq) (+ (* -5.86 (robot_p)) 8.5849))
                                (+ (robot_a_sq) (+ (* -1.84 (robot_a)) 0.8464)))))
                        (+ (* 1.0
                                (+ (+ (human_e_sq) (+ (* -6.88 (human_e)) 11.8336))
                                    (+ (+ (human_p_sq) (+ (* -5.86 (human_p)) 8.5849))
                                    (+ (human_a_sq) (+ (* -1.84 (human_a)) 0.8464)))))
                            (+ (* 1.0
                                    (+ (+ (robot_e_sq) (+ (* -6.88 (robot_e)) 11.8336))
                                        (+ (+ (robot_p_sq) (+ (* -5.86 (robot_p)) 8.5849))
                                        (+ (robot_a_sq) (+ (* -1.84 (robot_a)) 0.8464)))))
                                (* 1.0
                                    (+ (+ (human_e_sq) (+ (* -6.88 (human_e)) 11.8336))
                                        (+ (+ (human_p_sq) (+ (* -5.86 (human_p)) 8.5849))
                                        (+ (human_a_sq) (+ (* -1.84 (human_a)) 0.8464)))))))))))
            (not (emotion_checked))
            (increase (n_questions) 1)
            (increase (n_hard) 1)
            (assign (robot_e) 3.44)
            (assign (robot_p) 2.93)
            (assign (robot_a) 0.92)
            (assign (robot_e_sq) 11.8336)
            (assign (robot_p_sq) 8.5849)
            (assign (robot_a_sq) 0.8464)
            (assign (human_e) 3.44)
            (assign (human_p) 2.93)
            (assign (human_a) 0.92)
            (assign (human_e_sq) 11.8336)
            (assign (human_p_sq) 8.5849)
            (assign (human_a_sq) 0.8464)
            (increase (sound_uses) 1)
        )
    )

    (:action image_hard
        :parameters ()
        :precondition (and 
            (interaction_started)
            (quiz_introduced)
            (emotion_checked)
            (< (image_uses) (category_limit))
            (> (n_easy) (difficulty_limit))
            (> (n_medium) (difficulty_limit))
            ;(<= (n_hard) (difficulty_limit))
            (>= (human_e) 0.0)
            (>= (robot_e) 0.0)
            (not (can_conversate))
            (not (answered_wrong))
        )
        :effect (and 
            (increase (total-cost)
                (+ (image_coeff)
                    (+ (image_hard_coeff) (+ (* 1.0
                            (+ (+ (robot_e_sq) (+ (* -6.88 (robot_e)) 11.8336))
                                (+ (+ (robot_p_sq) (+ (* -5.86 (robot_p)) 8.5849))
                                (+ (robot_a_sq) (+ (* -1.84 (robot_a)) 0.8464)))))
                        (+ (* 1.0
                                (+ (+ (human_e_sq) (+ (* -6.88 (human_e)) 11.8336))
                                    (+ (+ (human_p_sq) (+ (* -5.86 (human_p)) 8.5849))
                                    (+ (human_a_sq) (+ (* -1.84 (human_a)) 0.8464)))))
                            (+ (* 1.0
                                    (+ (+ (robot_e_sq) (+ (* -6.88 (robot_e)) 11.8336))
                                        (+ (+ (robot_p_sq) (+ (* -5.86 (robot_p)) 8.5849))
                                        (+ (robot_a_sq) (+ (* -1.84 (robot_a)) 0.8464)))))
                                (* 1.0
                                    (+ (+ (human_e_sq) (+ (* -6.88 (human_e)) 11.8336))
                                        (+ (+ (human_p_sq) (+ (* -5.86 (human_p)) 8.5849))
                                        (+ (human_a_sq) (+ (* -1.84 (human_a)) 0.8464)))))))))))
            (not (emotion_checked))
            (increase (n_questions) 1)
            (increase (n_hard) 1)
            (assign (robot_e) 3.44)
            (assign (robot_p) 2.93)
            (assign (robot_a) 0.92)
            (assign (robot_e_sq) 11.8336)
            (assign (robot_p_sq) 8.5849)
            (assign (robot_a_sq) 0.8464)
            (assign (human_e) 3.44)
            (assign (human_p) 2.93)
            (assign (human_a) 0.92)
            (assign (human_e_sq) 11.8336)
            (assign (human_p_sq) 8.5849)
            (assign (human_a_sq) 0.8464)
            (increase (image_uses) 1)
        )
    )

    (:action ask_hard
        :parameters ()
        :precondition (and 
            (interaction_started)
            (quiz_introduced)
            (emotion_checked)
            (< (ask_uses) (category_limit_bonus))
            (> (n_easy) (difficulty_limit))
            (> (n_medium) (difficulty_limit))
            ;(<= (n_hard) (difficulty_limit))
            (>= (human_e) 0.0)
            (>= (robot_e) 0.0)
            (not (can_conversate))
            (not (answered_wrong))
        )
        :effect (and
            (increase (total-cost)
                (+ (ask_coeff)
                    (+ (ask_hard_coeff) (+ (* 1.0
                            (+ (+ (robot_e_sq) (+ (* -6.88 (robot_e)) 11.8336))
                                (+ (+ (robot_p_sq) (+ (* -5.86 (robot_p)) 8.5849))
                                (+ (robot_a_sq) (+ (* -1.84 (robot_a)) 0.8464)))))
                        (+ (* 1.0
                                (+ (+ (human_e_sq) (+ (* -6.88 (human_e)) 11.8336))
                                    (+ (+ (human_p_sq) (+ (* -5.86 (human_p)) 8.5849))
                                    (+ (human_a_sq) (+ (* -1.84 (human_a)) 0.8464)))))
                            (+ (* 1.0
                                    (+ (+ (robot_e_sq) (+ (* -6.88 (robot_e)) 11.8336))
                                        (+ (+ (robot_p_sq) (+ (* -5.86 (robot_p)) 8.5849))
                                        (+ (robot_a_sq) (+ (* -1.84 (robot_a)) 0.8464)))))
                                (* 1.0
                                    (+ (+ (human_e_sq) (+ (* -6.88 (human_e)) 11.8336))
                                        (+ (+ (human_p_sq) (+ (* -5.86 (human_p)) 8.5849))
                                        (+ (human_a_sq) (+ (* -1.84 (human_a)) 0.8464)))))))))))
            (not (emotion_checked))
            (increase (n_questions) 1)
            (increase (n_hard) 1)
            (assign (robot_e) 3.44)
            (assign (robot_p) 2.93)
            (assign (robot_a) 0.92)
            (assign (robot_e_sq) 11.8336)
            (assign (robot_p_sq) 8.5849)
            (assign (robot_a_sq) 0.8464)
            (assign (human_e) 3.44)
            (assign (human_p) 2.93)
            (assign (human_a) 0.92)
            (assign (human_e_sq) 11.8336)
            (assign (human_p_sq) 8.5849)
            (assign (human_a_sq) 0.8464)
            (increase (ask_uses) 1)
        )
    )

    
    ;; ROBOT --> HUMAN

    (:action comfort
        :parameters ()
        :precondition (and 
            (quiz_introduced)
            (emotion_checked)
            (> (robot_e) 0.0)
            (not (= (human_e) -1.85))
            ;(or (= (human_p) -2.29) (answered_wrong))
        )
        :effect (and 
            (increase (total-cost)
                (* 1.0
                    (+ (* 1.0
                            (+ (+ (robot_e_sq) (+ (* -6.88 (robot_e)) 11.8336))
                                (+ (+ (robot_p_sq) (+ (* -5.86 (robot_p)) 8.5849))
                                (+ (robot_a_sq) (+ (* -1.84 (robot_a)) 0.8464)))))
                        (+ (* 10.0
                                (+ (+ (human_e_sq) (+ (* 4.58 (human_e)) 5.2441))
                                    (+ (+ (human_p_sq) (+ (* 2.88 (human_p)) 2.0736))
                                    (+ (human_a_sq) (+ (* 4.08 (human_a)) 4.1616)))))
                            (+ (* 1.0
                                    (+ (+ (robot_e_sq) (+ (* -6.88 (robot_e)) 11.8336))
                                        (+ (+ (robot_p_sq) (+ (* -5.86 (robot_p)) 8.5849))
                                        (+ (robot_a_sq) (+ (* -1.84 (robot_a)) 0.8464)))))
                                (* 1.0
                                    (+ (+ (human_e_sq) (+ (* -6.88 (human_e)) 11.8336))
                                        (+ (+ (human_p_sq) (+ (* -5.86 (human_p)) 8.5849))
                                        (+ (human_a_sq) (+ (* -1.84 (human_a)) 0.8464)))))))))
            )  
            (assign (robot_e) 3.44)
            (assign (robot_p) 2.93)
            (assign (robot_a) 0.92)
            (assign (robot_e_sq) 11.8336)
            (assign (robot_p_sq) 8.5849)
            (assign (robot_a_sq) 0.8464)
            (assign (human_e) 3.44)
            (assign (human_p) 2.93)
            (assign (human_a) 0.92)
            (assign (human_e_sq) 11.8336)
            (assign (human_p_sq) 8.5849)
            (assign (human_a_sq) 0.8464)
            (not (answered_wrong))
            (assign (n_easy) 0)
            (assign (n_medium) 0)
            (not (emotion_checked))
        )
    )


    (:action take_a_break
        :parameters ()
        :precondition (and 
            (quiz_introduced)
            (emotion_checked)
            (> (robot_e) 0.0)
            (not (= (human_e) -1.85))
            ;(= (human_p) 0.57)
        )
        :effect (and 
            (increase (total-cost)
                (* 1.0
                    (+ (* 1.0
                            (+ (+ (robot_e_sq) (+ (* -6.88 (robot_e)) 11.8336))
                                (+ (+ (robot_p_sq) (+ (* -5.86 (robot_p)) 8.5849))
                                (+ (robot_a_sq) (+ (* -1.84 (robot_a)) 0.8464)))))
                        (+ (* 10.0
                                (+ (+ (human_e_sq) (+ (* 3.54 (human_e)) 3.1329))
                                    (+ (+ (human_p_sq) (+ (* -1.14 (human_p)) 0.3249))
                                    (+ (human_a_sq) (+ (* -3.60 (human_a)) 3.24)))))
                            (+ (* 1.0
                                    (+ (+ (robot_e_sq) (+ (* -6.88 (robot_e)) 11.8336))
                                        (+ (+ (robot_p_sq) (+ (* -5.86 (robot_p)) 8.5849))
                                        (+ (robot_a_sq) (+ (* -1.84 (robot_a)) 0.8464)))))
                                (* 1.0
                                    (+ (+ (human_e_sq) (+ (* -6.88 (human_e)) 11.8336))
                                        (+ (+ (human_p_sq) (+ (* -5.86 (human_p)) 8.5849))
                                        (+ (human_a_sq) (+ (* -1.84 (human_a)) 0.8464)))))))))
            )
            (assign (robot_e) 3.44)
            (assign (robot_p) 2.93)
            (assign (robot_a) 0.92)
            (assign (robot_e_sq) 11.8336)
            (assign (robot_p_sq) 8.5849)
            (assign (robot_a_sq) 0.8464)
            (assign (human_e) 3.44)
            (assign (human_p) 2.93)
            (assign (human_a) 0.92)
            (assign (human_e_sq) 11.8336)
            (assign (human_p_sq) 8.5849)
            (assign (human_a_sq) 0.8464)
            (not (emotion_checked))
            ;(can_conversate)
        )
    )
    
    (:action spark_curiosity
        :parameters ()
        :precondition (and 
            (quiz_introduced)
            (emotion_checked)
            (> (robot_e) 0.0)
            (not (= (human_e) -1.85))
            ;(= (human_e) -1.85)
        )
        :effect (and 
            (increase (total-cost)
                (* 1.0
                    (+ (* 1.0
                            (+ (+ (robot_e_sq) (+ (* -6.88 (robot_e)) 11.8336))
                                (+ (+ (robot_p_sq) (+ (* -5.86 (robot_p)) 8.5849))
                                (+ (robot_a_sq) (+ (* -1.84 (robot_a)) 0.8464)))))
                        (+ (* 10.0
                                (+ (+ (human_e_sq) (+ (* 4.54 (human_e)) 5.1529))
                                    (+ (+ (human_p_sq) (+ (* -0.44 (human_p)) 0.0484))
                                    (+ (human_a_sq) (+ (* -0.86 (human_a)) 0.1849)))))
                            (+ (* 1.0
                                    (+ (+ (robot_e_sq) (+ (* -6.88 (robot_e)) 11.8336))
                                        (+ (+ (robot_p_sq) (+ (* -5.86 (robot_p)) 8.5849))
                                        (+ (robot_a_sq) (+ (* -1.84 (robot_a)) 0.8464)))))
                                (* 1.0
                                    (+ (+ (human_e_sq) (+ (* -6.88 (human_e)) 11.8336))
                                        (+ (+ (human_p_sq) (+ (* -5.86 (human_p)) 8.5849))
                                        (+ (human_a_sq) (+ (* -1.84 (human_a)) 0.8464)))))))))
            )
            (assign (robot_e) 3.44)
            (assign (robot_p) 2.93)
            (assign (robot_a) 0.92)
            (assign (robot_e_sq) 11.8336)
            (assign (robot_p_sq) 8.5849)
            (assign (robot_a_sq) 0.8464)
            (assign (human_e) 3.44)
            (assign (human_p) 2.93)
            (assign (human_a) 0.92)
            (assign (human_e_sq) 11.8336)
            (assign (human_p_sq) 8.5849)
            (assign (human_a_sq) 0.8464)
            (not (emotion_checked))
        )
    )

    (:action tell_a_joke
        :parameters ()
        :precondition (and 
            (quiz_introduced)
            (emotion_checked)
            (> (robot_e) 0.0)
            (not (= (human_e) -1.85))
            ;(= (human_p) -1.04)
        )
        :effect (and 
            (increase (total-cost)
                (* 1.0
                    (+ (* 1.0
                            (+ (+ (robot_e_sq) (+ (* -6.88 (robot_e)) 11.8336))
                                (+ (+ (robot_p_sq) (+ (* -5.86 (robot_p)) 8.5849))
                                (+ (robot_a_sq) (+ (* -1.84 (robot_a)) 0.8464)))))
                        (+ (* 10.0
                                (+ (+ (human_e_sq) (+ (* 4.74 (human_e)) 5.6169))
                                    (+ (+ (human_p_sq) (+ (* 2.08 (human_p)) 1.0816))
                                    (+ (human_a_sq) (+ (* 1.42 (human_a)) 0.5041)))))
                            (+ (* 1.0
                                    (+ (+ (robot_e_sq) (+ (* -6.88 (robot_e)) 11.8336))
                                        (+ (+ (robot_p_sq) (+ (* -5.86 (robot_p)) 8.5849))
                                        (+ (robot_a_sq) (+ (* -1.84 (robot_a)) 0.8464)))))
                                (* 1.0
                                    (+ (+ (human_e_sq) (+ (* -6.88 (human_e)) 11.8336))
                                        (+ (+ (human_p_sq) (+ (* -5.86 (human_p)) 8.5849))
                                        (+ (human_a_sq) (+ (* -1.84 (human_a)) 0.8464)))))))))
            )
            (assign (robot_e) 3.44)
            (assign (robot_p) 2.93)
            (assign (robot_a) 0.92)
            (assign (robot_e_sq) 11.8336)
            (assign (robot_p_sq) 8.5849)
            (assign (robot_a_sq) 0.8464)
            (assign (human_e) 3.44)
            (assign (human_p) 2.93)
            (assign (human_a) 0.92)
            (assign (human_e_sq) 11.8336)
            (assign (human_p_sq) 8.5849)
            (assign (human_a_sq) 0.8464)
            (not (emotion_checked))
        )
    )

    (:action raise_stakes
        :parameters ()
        :precondition (and 
            (quiz_introduced)
            (emotion_checked)
            (> (robot_e) 0.0)
            ;(= (human_p) 0.22)
        )
        :effect (and 
            (increase (total-cost)
                (* 1.0
                    (+ (* 1.0
                            (+ (+ (robot_e_sq) (+ (* -6.88 (robot_e)) 11.8336))
                                (+ (+ (robot_p_sq) (+ (* -5.86 (robot_p)) 8.5849))
                                (+ (robot_a_sq) (+ (* -1.84 (robot_a)) 0.8464)))))
                        (+ (* 10.0
                                (+ (+ (human_e_sq) (+ (* 3.70 (human_e)) 3.4225))
                                    (+ (+ (human_p_sq) (+ (* 1.72 (human_p)) 0.7396))
                                    (+ (human_a_sq) (+ (* 4.02 (human_a)) 4.0401)))))
                            (+ (* 1.0
                                    (+ (+ (robot_e_sq) (+ (* -6.88 (robot_e)) 11.8336))
                                        (+ (+ (robot_p_sq) (+ (* -5.86 (robot_p)) 8.5849))
                                        (+ (robot_a_sq) (+ (* -1.84 (robot_a)) 0.8464)))))
                                (* 1.0
                                    (+ (+ (human_e_sq) (+ (* -6.88 (human_e)) 11.8336))
                                        (+ (+ (human_p_sq) (+ (* -5.86 (human_p)) 8.5849))
                                        (+ (human_a_sq) (+ (* -1.84 (human_a)) 0.8464)))))))))
            )
            (assign (robot_e) 3.44)
            (assign (robot_p) 2.93)
            (assign (robot_a) 0.92)
            (assign (robot_e_sq) 11.8336)
            (assign (robot_p_sq) 8.5849)
            (assign (robot_a_sq) 0.8464)
            (assign (human_e) 3.44)
            (assign (human_p) 2.93)
            (assign (human_a) 0.92)
            (assign (human_e_sq) 11.8336)
            (assign (human_p_sq) 8.5849)
            (assign (human_a_sq) 0.8464)
            (not (emotion_checked))
            (assign (n_easy) 3)
            (assign (n_medium) 3)
        )
    )


    ;; ROBOT --> ROBOT

    (:action calm_down
        :parameters ()
        :precondition (and 
            (quiz_introduced)
            (emotion_checked)
            ;(= (robot_p) 0.57)
        )
        :effect (and 
            (increase (total-cost)
                (* 1.0
                    (+ (* 1.0
                            (+ (+ (robot_e_sq) (+ (* 3.54 (robot_e)) 3.1329))
                                (+ (+ (robot_p_sq) (+ (* -1.14 (robot_p)) 0.3249))
                                (+ (robot_a_sq) (+ (* -3.60 (robot_a)) 3.24)))))
                        (* 1.0
                            (+ (+ (robot_e_sq) (+ (* -6.88 (robot_e)) 11.8336))
                                (+ (+ (robot_p_sq) (+ (* -5.86 (robot_p)) 8.5849))
                                (+ (robot_a_sq) (+ (* -1.84 (robot_a)) 0.8464))))))))
            (assign (robot_e) 3.44)
            (assign (robot_p) 2.93)
            (assign (robot_a) 0.92)
            (assign (robot_e_sq) 11.8336)
            (assign (robot_p_sq) 8.5849)
            (assign (robot_a_sq) 0.8464)
            (not (emotion_checked))
        )
    )

    (:action ask_for_help
        :parameters ()
        :precondition (and 
            (quiz_introduced)
            (emotion_checked)
            ;(<= (robot_e) -2.30)
        )
        :effect (and 
            (increase (total-cost)
                (* 1.0
                    (+ (* 1.0
                            (+ (+ (robot_e_sq) (+ (* 4.74 (robot_e)) 5.6169))
                                (+ (+ (robot_p_sq) (+ (* 2.08 (robot_p)) 1.0816))
                                (+ (robot_a_sq) (+ (* 1.42 (robot_a)) 0.5041)))))
                        (* 1.0
                            (+ (+ (robot_e_sq) (+ (* -6.88 (robot_e)) 11.8336))
                                (+ (+ (robot_p_sq) (+ (* -5.86 (robot_p)) 8.5849))
                                (+ (robot_a_sq) (+ (* -1.84 (robot_a)) 0.8464))))))))
            (assign (robot_e) 3.44)
            (assign (robot_p) 2.93)
            (assign (robot_a) 0.92)
            (assign (robot_e_sq) 11.8336)
            (assign (robot_p_sq) 8.5849)
            (assign (robot_a_sq) 0.8464)
            (not (emotion_checked))
        )
    )

    (:action show_vulnerability
        :parameters ()
        :precondition (and 
            (quiz_introduced)
            (emotion_checked)
            ;(= (robot_e) -2.29)
        )
        :effect (and 
            (increase (total-cost)
                (* 1.0
                    (+ (* 1.0
                            (+ (+ (robot_e_sq) (+ (* 4.58 (robot_e)) 5.2441))
                                (+ (+ (robot_p_sq) (+ (* 2.88 (robot_p)) 2.0736))
                                (+ (robot_a_sq) (+ (* 4.08 (robot_a)) 4.1616)))))
                        (* 1.0
                            (+ (+ (robot_e_sq) (+ (* -6.88 (robot_e)) 11.8336))
                                (+ (+ (robot_p_sq) (+ (* -5.86 (robot_p)) 8.5849))
                                (+ (robot_a_sq) (+ (* -1.84 (robot_a)) 0.8464))))))))
            (assign (robot_e) 3.44)
            (assign (robot_p) 2.93)
            (assign (robot_a) 0.92)
            (assign (robot_e_sq) 11.8336)
            (assign (robot_p_sq) 8.5849)
            (assign (robot_a_sq) 0.8464)
            (not (emotion_checked))
        )
    )

    (:action reset_emotion
        :parameters ()
        :precondition (and 
            (quiz_introduced)
            (emotion_checked)
            (not (= (robot_e) -2.37))
            (not (= (robot_e) -1.77))
            (not (= (robot_e) -2.29))
            ;(or (= (robot_e) -2.27) (= (robot_e) 0.50))
        )
        :effect (and 
            (increase (total-cost)
                (* 1.0
                    (+ (+ (robot_e_sq) (+ (* -6.88 (robot_e)) 11.8336))
                        (+ (+ (robot_p_sq) (+ (* -5.86 (robot_p)) 8.5849))
                        (+ (robot_a_sq) (+ (* -1.84 (robot_a)) 0.8464))))))
            (assign (robot_e) 3.44)
            (assign (robot_p) 2.93)
            (assign (robot_a) 0.92)
            (assign (robot_e_sq) 11.8336)
            (assign (robot_p_sq) 8.5849)
            (assign (robot_a_sq) 0.8464)
            (not (emotion_checked))
        )
    )

)
