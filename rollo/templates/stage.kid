<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
<meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
<title>Rollo</title>
</head>
<body>

<h1><a href="/category/${stage.deployment.application.category.id}/">${stage.deployment.application.category.name}</a> :
<a
   href="/application/${stage.deployment.application.id}/">${stage.deployment.application.name}</a> : 
<a href="/deployment/${stage.deployment.id}/">${stage.deployment.name}</a> : 
stage ${stage.cardinality} - ${stage.name}</h1>

<form action="edit" method="post">
<table>
<tr><th>order</th><td><input type="text" size="2" name="cardinality" value="${stage.cardinality}"/></td></tr>
<tr><th>name</th><td><input type="text" name="name" value="${stage.name}"/></td></tr>
<tr><th>recipe</th>

<td py:if="stage.recipe.name">
<a href="/cookbook/${stage.recipe.id}/">${stage.recipe.name}</a>. Edit
in the cookbook, or select a different one: <select name="recipe_id">
<option value="">- Custom Recipe -</option>
<span py:for="recipe in all_recipes">
<option value="${recipe.id}" py:if="recipe.id == stage.recipe.id"
selected="selected">${recipe.name}</option>
<option value="${recipe.id}" py:if="recipe.id !=
stage.recipe.id">${recipe.name}</option>
</span>
</select>
</td>

<td py:if="not stage.recipe.name">
Select a Cookbook recipe <select
name="recipe_id">
<option value="">None - Add code below</option>
<option py:for="recipe in all_recipes" value="${recipe.id}">${recipe.name}</option>
</select><br />
Or edit code:<br />

<select name="language">
<option py:if="stage.recipe.language == 'python'" value="python" selected="selected">python</option>
<option py:if="stage.recipe.language != 'python'" value="python">python</option>
<option py:if="stage.recipe.language == 'shell'" value="shell" selected="selected">shell</option>
<option py:if="stage.recipe.language != 'shell'" value="shell">shell</option>
</select>
(<a href="/cookbook/${stage.recipe.id}/">promote this recipe to the cookbook</a>)
<br />
<textarea name="code" cols="60" rows="5" class="resizable">${stage.recipe.code}</textarea>


</td></tr>
</table><input type="submit" value="edit" />

</form>

<hr />

<form action="delete" method="post">
<fieldset><legend>delete stage</legend>

Delete this stage: <input type="submit" value="DELETE" />

</fieldset>
</form>

</body>
</html>
