<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
<meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
<title>Rollo</title>
</head>
<body>

<h1><a href="/cookbook/">Cookbook</a>: ${recipe.name}</h1>

<form action="edit" method="post">
<table>
<tr><th>name</th>
<td><input type="text" name="name" value="${recipe.name}"/>
<span style="color: #f00" py:if="recipe.name == ''">You must give this recipe a name to
  enter it in the cookbook</span>
</td></tr>
<tr><th>description</th>
<td><textarea name="description" rows="5" cols="60" class="resizable">${recipe.description}</textarea></td>
</tr>

<tr><th>code</th>
<td>
language <select name="language">
<span py:if="recipe.language == 'python'">
<option value="python" selected="selected">python</option>
<option value="shell">shell</option>
</span>
<span py:if="recipe.language == 'shell'">
<option value="python">python</option>
<option value="shell" selected="selected">shell</option>
</span>

</select><br />
<textarea name="code" rows="5" cols="60" class="resizable">${recipe.code}</textarea></td>
</tr>


</table>
<input type="submit" value="save"/>
</form>

<div py:if="recipe.stages">
<h2>Deployments using this recipe</h2>
<table width="100%">
<tr py:for="i,stage in enumerate(recipe.stages)" class="${i%2 and 'odd' or 'even'}">
<td>
<a
   href="/category/${stage.deployment.application.category.id}/">${stage.deployment.application.category.name}</a>
   :
<a
   href="/application/${stage.deployment.application.id}/">${stage.deployment.application.name}</a> :
<a href="/deployment/${stage.deployment.id}/">${stage.deployment.name}</a></td>
</tr>
</table>
</div>
<hr />
<form action="delete" method="post">
<fieldset><legend>delete recipe</legend>
<input type="submit" value="DELETE" />
</fieldset>
</form>
</body>
</html>
