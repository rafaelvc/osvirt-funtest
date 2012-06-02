<?php
    include('../inc/header.php');
?>

// globals
var updater;
var stack;

function stopRKey(evt) {
    var evt = (evt) ? evt : ((event) ? event : null);
    var node = (evt.target) ? evt.target : ((evt.srcElement) ? evt.srcElement : null);
    if ((evt.keyCode == 13) && ((node.type=="text") || (node.type=="password")))  {return false;}
}

// use to launch the rpm installation
function install_rpms(info) {

    // set global var
    stack = info;

    // the the packages to install
    packages = "";
    for(i=0;i<$('form-wizard').elements.length;i++) {
        if($('form-wizard').elements[i].checked == true && $('form-wizard').elements[i].disabled == false) {
            packages += $('form-wizard').elements[i].value+';';
        }
    }

    if(stack == "mds") {
        $('config_install').onclick = function() {
            window.location.href = "wiz_conf.php?groups="+packages;
        }
    }

    if(!packages.empty()) {
        // launch rpm install
        new Ajax.Request('wiz_rpm.php?packages='+packages+'&stack='+stack, {
            method: 'get',
            onSuccess: refresh
        });
    }
    else {
        $('task').innerHTML = '<strong class="nok"><?=_("You didn\\'t select any component.")?></strong>';
        // make sure to disable the button
        if(stack == "mds") 
            $('config_install').disabled = true;
        $('close_install').disabled = false;
        $('config_detail').disabled = true;
        // show the install popup
        $('overlay').show();
        $('install').show();
    }
}

// use to refresh the install log every 1s
function refresh(response) {
    // get packages and stack name
    try {
        info = response.responseText.evalJSON();
        error = false;
    }
    catch(e) {
        info = response.responseText;
        error = true;
        // not an error, just logout from AJAX call
        if(info == "logout") {
            window.location.href = "/mmc-wizard/";
        }
    }

    if(!error) {
        // set some text
        text = '<?=_('Installation of')?> <strong>';
        // name of stacks
        for(i=0; i<info.length; i++) {
            text += info[i].title+', ';
        }
        text = text.slice(0, text.length-2);
        text += ' : </strong><code>'
        // name of packages
        for(i=0; i<info.length; i++) {
            for(j=0;j<info[i].packages.length;j++) {
                text += info[i].packages[j]+', ';
            }
        }
        text = text.slice(0, text.length-2);
        text += '</code><br/><br/><strong><?=_('Stand by while installing')?> </strong><img src="images/load.gif" style="vertical-align: bottom;" />';
        $('task').innerHTML = text;
        // make sure to disable the button
        if(stack == "mds") 
            $('config_install').disabled = true;
        $('close_install').disabled = true;
        $('config_detail').disabled = false;
        // show the install popup
        $('overlay').show();
        $('install').show();

        // refresh log
        updater = new PeriodicalExecuter(refresh_log, 1);
    }
    else {
        if(info != "logout")
            alert(info);
    }
}

function refresh_log() {
    new Ajax.Request('wiz_install.php', {
        method: 'get',
        on200: check_install
    });
}

// check if install is finished every refresh
function check_install(response) {
    text = response.responseText.strip();
    //code = text[text.length-4];
    code = text.slice(text.length-4, text.length-3);
    $('log').scrollTop = $('log').scrollHeight;
    if(text.endsWith('END')) {
        // stop updating
        updater.stop();
        // make sure we have the text
        text = text.slice(0, text.length-4);
        $('log').innerHTML = text;
        if(code == '0') {
            if(stack == "mds") {
                $('task').innerHTML = '<strong class="ok"><?=_('Installation successfull. You can now configure the services.')?></strong>';
                $('config_install').disabled = false;
            }
            else
                $('task').innerHTML = '<strong class="ok"><?=_('Installation successfull.')?></strong>';
        }
        else {
            $('task').innerHTML = '<strong class="nok"><?=('Installation terminated with errors. Check the details below.')?></strong>';
            // show the log if error
            $('log').show();
            if(stack == "mds") {
                // make sure to disable the button
                $('config_install').disabled = true;
            }
        }
        $('close_install').disabled = false;
    }
    $('log').innerHTML = text;
}

function reload() {
    // just reload the page
    window.location.reload();
}

function always_on(input) {
    input.checked = true;
}

