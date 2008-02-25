<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
<meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
<title>Rollo</title>
    <!-- we repeat the mochikit inclusion here to make sure it's
    loaded before push.js -->
    
    <script type="text/javascript"
    src="/static/javascript/MochiKit/MochiKit.js"></script>
<script type="text/javascript" src="/static/javascript/push.js"></script>

</head>
<body>

<h1>Push: <a
       href="/category/${push.deployment.application.category.id}/">${push.deployment.application.category.name}</a> 
: 
<a
       href="/application/${push.deployment.application.id}/">${push.deployment.application.name}</a> : <a href="/deployment/${push.deployment.id}/">${push.deployment.name}</a></h1>

<p py:if="push.comment">${push.comment}</p>

<p>Started at <b>${push.start_time}</b> by <b>${push.user.uni}</b></p>

<div id="push-status" class="${push.status}">${push.status}</div>

<div py:if="not push.pushstages">
<!-- the push hasn't actually happened yet. we add the interface doing that here -->

<input py:if="step" type="submit" value="run all stages" id="runall-button"
       onclick="runAllStages();this.disabled=true;return false" />

<!-- the presence of this input tells the js to run the steps
     as soon as the page loads:  -->
<input py:if="not step" type="hidden" value="autorun" id="autorun"
       name="autorun" />

<input py:if="rollback" type="hidden" value="${rollback}"
       id="rollback" name="rollback" />


<h2>stages</h2>

<table style="width: 100%">
<tr class="unknown stage-row" py:for="stage in push.deployment.stages" id="stage-${stage.id}">
<th>${stage.name}</th>
<td><input py:if="step" type="submit" value="execute" id="execute-${stage.id}"
onclick="runStage(${stage.id}); this.disabled=true;return false" />
<input py:if="not step" type="hidden" value="execute" id="execute-${stage.id}"
 />
</td>
</tr>
</table>
</div>

<div py:if="push.pushstages">


<form py:if="push.rollback_url and push.status == 'ok'" action="/deployment/${push.deployment.id}/rollback" method="post">
<fieldset><legend>Rollback to this Push</legend>
<input type="hidden" name="push_id" value="${push.id}" />
comment <input type="text" name="comment" /> (<input type="checkbox"
						     name="step" />
  step) <input type="submit" value="ROLLBACK" />
</fieldset>
</form>

<h2>stages</h2>
<table style="width: 100%">
<span py:for="pushstage in reversed(push.pushstages)">
<tr class="${pushstage.status} pushstage-row" id="pushstage-${pushstage.id}">
<th>${pushstage.stage.name}</th>
<td>${pushstage.end_time}</td>
</tr>

<span py:for="log in pushstage.logs">
<tr py:if="log.command">
  <td colspan="2" class="command"><h3>Code</h3><pre>${log.command}</pre></td>
</tr>
<tr py:if="log.stdout">
  <td colspan="2" class="stdout"><h3>STDOUT</h3><pre>${log.stdout}</pre></td>
</tr>
<tr py:if="log.stderr">
  <td colspan="2" class="stderr"><h3>STDERR</h3><pre>${log.stderr}</pre></td>
</tr>
</span>

</span>
</table>

<form action="delete" method="POST">
<fieldset><legend>delete</legend>
Delete this push <input type="submit" value="DELETE" />
</fieldset>
</form>

</div>


</body>
</html>
