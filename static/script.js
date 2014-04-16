function Listener(config) {
    var $this = this;
	this.recognizer = new window.SpeechRecognition();
	this.isListening = false;

    defaults = {
        maxAlternatives: 5,
        continuous: false
    };

    config = $.extend({}, defaults, config);
    if (typeof(config) == 'object') {
        $.each(config, function(key, value) {
            $this.recognizer[key] = value;
        });
    }

	this.recognizer.onresult = function(e) {
		if (this.onresult) {
			this.onresult(e);
		}
	}.bind(this);

	this.recognizer.nomatch = function(e) {
		if (this.nomatch) {
			this.nomatch(e);
		}
	}.bind(this);

	this.recognizer.onstart = function(e) {
		if (this.onstart) {
			this.onstart(e);
		}
	}.bind(this);

	this.recognizer.onend = function(e) {
		if (this.onend) {
			this.onend(e);
		}
	}.bind(this);

	this.recognizer.onerror = function(e) {
		console.log('recog error', e);
	}.bind(this);

    this.start = function() {
        if (!this.isListening) {
            $this.recognizer.start();
        }

        $this.isListening = true;
    };

    this.stop = function() {
        if (this.isListening) {
            $this.recognizer.stop();
        }

        $this.isListening = false;
    };

    this.setGrammars = function(grammars) {
        $.each(grammars, function() {
            console.log(this)
            $this.recognizer.grammars.addFromUri(this);
        });
    };

};


function Speaker(config) {
    this.isTalking = false;

    this.DEST_LANG = 'en';

    this.speak = function(txt, onend) {
        var $this = this;
        this.isTaking = true;

        // Need to latinize the text.
        // Remove when https://code.google.com/p/chromium/issues/detail?id=333515 is fixed.
        var sanitized = latinize(txt);
        var msg = new SpeechSynthesisUtterance();
        msg.text = sanitized;
        msg.lang = this.DEST_LANG;

        msg.onend = function(e) {
            $this.isTaking = false;

            console.log('Finished at ' + e.elapsedTime + ' seconds.');
            if (onend) {
                onend(e);
            }
        };

        speechSynthesis.speak(msg);
    };
}

function DM(config) {
    var $this = this,
        parameters = {},
        speaker = new Speaker(),
        listener = new Listener(),
        status = '',
        param_key,
        param_value_guess;

    var defaults = {
        'indicator': false,
        'progressBar': false
    };
    config = $.extend({}, defaults, config);

    listener.onstart = function(e) {
        console.log('listening began', e);
        if (config['indicator']) {
            $(config['indicator']).find("#mic-off").hide();
            $(config['indicator']).find("#mic-on").show();
        }
    }

    listener.onend = function(e) {
        console.log('listening ended', e);
        if (config['indicator']) {
            $(config['indicator']).find("#mic-off").show();
            $(config['indicator']).find("#mic-on").hide();
        }
    }

    listener.onresult = function(e) {
        console.log(e);
        if (e.results.length) {
            var result = e.results[e.resultIndex];
            if (result.isFinal) {
                var transcript = result[0].transcript,
                    confidence = result[0].confidence;

                if (config['monitor'] !== undefined) {
                    var history = config['monitor'].find('.say').html();
                    config['monitor'].children('.history').prepend('<p>' + history + ' <code>' + transcript + '</code> <span class="badge">' + confidence + '</span></p>');
                    config['monitor'].find('.say').html('')
                }

                if (status == 'ask') {
                    if (param_simple_grammar) {
                        var grammar = new simpleGrammarObject(param_simple_grammar);

                        // if the result of one of the alternatives is in grammar then it's ok to proceed
                        $.each(result, function(i, v) {
                            if (v.transcript) {
                                match = grammar.indexOf(v.transcript);
                            }
                            if (match !== false) {
                                return false;
                            }
                        });

                        if (match !== false) {
                            // do it!
                            update_params(param_key, match);
                        } else{
                            // repeat the question ...
                            speaker.speak("I didn't understand. Please answer: " + grammar.simpleChoices().join(" or ") + ".", function(){
                                console.log("grammar error");
                                ask(param_question, param_key, param_simple_grammar);
                            });
                        }
                    } else {
                        if (confidence > 0.7) {
                            // do it!
                            update_params(param_key, transcript);
                        } else {
                            // not sure about the answer then confirm the answer:
                            param_value_guess = transcript;
                            confirm("Did you say '" + param_value_guess + "'?");
                        }
                    }
                } else {
                    if (status == 'confirm') {
                        if (transcript == 'yes') {
                            update_params(param_key, param_value_guess);
                        } else {
                            if (transcript == 'no') {
                                speaker.speak("Please answer this question again.", function(){
                                    console.log("recognition error");
                                    ask(param_question, param_key, param_simple_grammar);
                                });
                            } else {
                                // the answer was neither "Yes" nor "No". confirm again:
                                reconfirm("Did you say '" + param_value_guess + "'?");
                            }
                        }
                    } else {
                        // is there any other unimplemented command?
                        console.log('invalid status?');
                        console.log('status:', status);
                    }
                }
                listener.stop();
            }
        }
    }

    var update_params = function(key, value) {
        parameters[key] = value;
        syncDB();
    }

    var reconfirm = function(question) {
        speaker.speak("Please answer 'yes' or 'no'!", function(){
            confirm(question);
        });
    }

    var confirm = function(question) {
        status = 'confirm';
        speaker.speak(question, function(){
            console.log(status);
            listener.start();
        });
    }

    var confirmedResult = function(transcript) {
        if (transcript == 'yes') {
            update_params(param_key, param_value_guess);
        } else {
            if (transcript == 'no') {
                // then what?
            } else {
                reconfirm("Did you say '" + param_value_guess + "'?");
            }
        }
    }

    var ask = function(question, answer, simpleGrammar) {
        simpleGrammar = typeof simpleGrammar !== 'undefined' ? simpleGrammar : false;
        status = 'ask';

        if (config['monitor'] !== undefined) {
            config['monitor'].find('.say').html(question);
        }

        speaker.speak(question, function(){
            param_key = answer;
            param_value_guess = '';
            param_simple_grammar = simpleGrammar;
            param_question = question
            listener.start();
        });
    }

    // send current parameters to db.
    // then follow the response, by doing the next step.
    var syncDB = function() {
        status = 'syncDB';
        console.log(parameters);
        if (config['loading'] !== undefined) {
            config['loading'].fadeIn();
        }
        $.ajax({
            url: '/dm',
            type: 'POST',
            dataType: 'json',
            data: parameters,
            success: function(data) {
                if (config['loading'] !== undefined) {
                    config['loading'].fadeOut();
                }
                // next step
                if (data['ask'] !== undefined) {
                    if (data['simple-grammar'] !== undefined) {
                        ask(data['ask'], data['param'], data['simple-grammar']);
                    } else {
                        ask(data['ask'], data['param']);
                    }
                } else {
                    if (data['end'] !== undefined) {
                        speaker.speak(data['end']);
                    } else {
                        // error?
                    }
                }

                if (data['progress'] !== undefined && config['progressBar']) {
                    $(config['progressBar'])
                        .attr("aria-valuenow", data['progress'])
                        .css('width', (data['progress'] * 5) + '%');
                }
            },
            error: function(e) {
                console.log("Error!", e);
            }
        });
    }

    this.begin = function(){

        syncDB();
    }
}

simpleGrammarObject =  function(grammar) {
    var $this = this;

    this.indexOf = function(transcript) {
        var match = false;
        $.each(grammar, function(i, v) {
            if (i === transcript) {
                match = v;
                return false;
            } else {
                if (v === transcript) {
                    match = v;
                    return false;
                }
            }
        });

        return match;
    }

    this.simpleChoices = function() {
        var keys = []

        $.each(grammar, function(i, v) {
            if (keys.indexOf(v) === -1) {
                // prepend new item to keys:
                keys.unshift(v);
            }
        });

        return keys;
    }
}