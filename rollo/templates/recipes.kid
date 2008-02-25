<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
<meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
<title>Rollo</title>
</head>
<body>


<h1>Cookbook</h1>

<table>
<tr><th>name</th><th>description</th><th>language</th><th>code</th></tr>

<tr py:for="recipe in all_recipes">
<th><a href="/cookbook/${recipe.id}/">${recipe.name}</a></th>
<td>${recipe.description}</td>
<td>${recipe.language}</td>
<td><pre>${recipe.code}</pre></td>
</tr>

</table>

<form action="add_recipe" method="post">
<fieldset><legend>add recipe</legend>
<table>
<tr><th>name</th>
<td><input type="text" name="name" /></td></tr>
<tr><th>description</th>
<td><textarea name="description" rows="5" cols="60" class="resizable"></textarea></td>
</tr>

<tr><th>code</th>
<td>
language <select name="language">
<option value="python">python</option>
<option value="shell">shell</option>
</select><br />
<textarea name="code" rows="5" cols="60" class="resizable"></textarea></td>
</tr>

</table>
<input type="submit" value="add recipe" />
</fieldset>
</form>

</body>
</html>
