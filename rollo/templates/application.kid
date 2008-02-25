<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
<meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
<title>Rollo</title>
</head>
<body>

<h1><a href="/category/${application.category.id}/">${application.category.name}</a> : ${application.name}</h1>

<div py:if="application.deployments">
<table width="100%">

<tr py:for="deployment in application.deployments" class="${deployment.status()}">
<th><a href="/deployment/${deployment.id}/">${deployment.name}</a></th></tr>

</table>

</div>

<form action="add_deployment" method="post">
<p>Add A New Deployment: <input type="text" name="name" /> <input
type="submit" value="Add" /></p>
</form>


<hr />
<form action="delete" method="post">
<p>Delete this application: <input type="submit" value="DELETE"/></p>
</form>

</body>
</html>
