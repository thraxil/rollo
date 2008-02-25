<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
<meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
<title>Rollo</title>
</head>
<body>

<h1>${category.name}</h1>


<div py:if="category.applications">
<table width="100%">

<span py:for="application in category.applications">
<tr class="application" ><th><h3><a href="/application/${application.id}/">${application.name}</a></h3></th></tr>
<tr class="deployment nested-${deployment.status()}" py:for="deployment in application.deployments"><th><a href="/deployment/${deployment.id}/">${deployment.name}</a></th></tr>
</span>

</table>

</div>

<form action="add_application" method="post">
<p>Add A New Application: <input type="text" name="name" /> <input
type="submit" value="Add" /></p>
</form>


<hr />
<form action="delete" method="post">
<p>Delete this category: <input type="submit" value="DELETE"/></p>
</form>

</body>
</html>
