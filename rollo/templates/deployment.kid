<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
<meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
<title>Rollo</title>
</head>
<body>

<h1><a
       href="/category/${deployment.application.category.id}/">${deployment.application.category.name}</a> 
: 
<a href="/application/${deployment.application.id}/">${deployment.application.name}</a> : ${deployment.name}</h1>

<div class="tabber">

<div class="tabbertab">
<h2>Push</h2>

<div py:if="deployment.pushes">

<div id="push-status" class="${deployment.pushes[0].status}">${deployment.pushes[0].status}</div>
</div>

<form action="push" method="post">
<fieldset><legend>Push</legend>

Comment: <input type="text" name="comment" /> (<input type="checkbox" name="step" /> step )<input type="submit" value="push" />
</fieldset>
</form>

<div py:if="deployment.pushes">

<table width="100%">
<tr py:for="push in deployment.pushes" class="${push.status}">
<th><a
       href="/push/${push.id}/">${tg.h.time_ago_in_words(push.start_time)} ago</a></th>
<td>${push.user.uni}</td>
<td>${push.comment}</td>
</tr>
</table>

</div>
</div>


<div class="tabbertab">
<h2>Settings</h2>

<div py:if="deployment.settings">

<form action="edit_settings" method="post">
<table width="100%">
<tr><th>name</th><th>value</th></tr>
<tr py:for="setting in deployment.settings">
<td><input type="text" name="setting_name_${setting.id}"
value="${setting.name}"  style="width: 100%"/></td>
<td><input type="text" name="setting_value_${setting.id}" 
value="${setting.value}" style="width: 100%" /></td>
</tr>
</table>
<input type="submit" value="save settings" />
</form>
</div>

<form action="add_setting" method="post">
<fieldset>
<legend>Add Setting</legend>
<table width="100%">
<tr><th>name</th><th>value</th></tr>
<tr><td><input type="text" name="name" style="width: 100%"/></td>
<td><input type="text" name="value" style="width: 100%"/></td>
</tr>
</table>
<input type="submit" value="Add" />
</fieldset>
</form>
</div>

<div class="tabbertab">
<h2>Stages</h2>
<div py:if="deployment.stages">

<table width="100%">
<tr py:for="stage in deployment.stages">
<th>${stage.cardinality} - <a href="/stage/${stage.id}/">${stage.name}</a></th>
<td><a py:if="stage.recipe.name"
href="/cookbook/${stage.recipe.id}/">Cookbook Recipe:
${stage.recipe.name}</a>
<div py:if="not
	    stage.recipe.name"><b>${stage.recipe.language}</b><br
								 /><div
	    class="code">${XML(stage.recipe.code_html())}</div></div>
</td>
</tr>
</table>
</div>

<form action="add_stage" method="post">
<fieldset><legend>Add Stage</legend>
<table>
<tr><th>name</th><td><input type="text" name="name"/></td></tr>
<tr><th>recipe</th><td>Select a Cookbook recipe <select
name="recipe_id">
<option value="">None - Add code below</option>
<option py:for="recipe in all_recipes" value="${recipe.id}">${recipe.name}</option>
</select><br />
Or enter new code:<br />
<select
   name="language"><option
		      value="python">python</option><option
						       value="shell">shell</option></select><br />
<textarea name="code" cols="60" rows="5" class="resizable"></textarea>

</td></tr>
</table><input type="submit" value="add stage" />

</fieldset>
</form>
</div>

<div class="tabbertab">
<h2>Clone</h2>
<form action="clone" method="post">
<p>Clone this deployment.</p>
<p>New deployment name: <input type="text" name="name" /></p>
<p>In Application: 

<select name="application_id">
<optgroup py:for="category in all_categories"
	  label="${category.name}">

<option 
py:for="application in category.applications"
py:attrs="dict(value=application.id, selected=(None, '')[application.id == deployment.application.id])"
>${application.name}</option>
</optgroup>
</select></p>

 <input type="submit" value="Clone"/>
</form>
</div>


<div class="tabbertab">
<h2>Delete</h2>
<form action="delete" method="post">
<p>Delete this deployment: <input type="submit" value="DELETE"/></p>
</form>
</div>
</div>


</body>
</html>
