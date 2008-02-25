<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
<meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
<title>Rollo</title>
</head>
<body>

<div py:if="recent_pushes">
<h1>Your Recent Pushes</h1>

<table width="100%">
<tr py:for="push in recent_pushes" class="${push.status}">
<th><a
       href="/category/${push.deployment.application.category.id}/">${push.deployment.application.category.name}</a>
       : 
<a
   href="/application/${push.deployment.application.id}/">${push.deployment.application.name}</a>
   :
<a
   href="/deployment/${push.deployment.id}/">${push.deployment.name}</a> :
<a href="/push/${push.id}/">${tg.h.time_ago_in_words(push.start_time)} ago</a></th>
<td>${push.comment}</td>
</tr>
</table>


</div>

<div py:if="categories.count()">
<h1>All Applications</h1>

<table width="100%">

<span py:for="category in categories">
<tr class="category"><th><h2><a href="/category/${category.id}/">${category.name}</a></h2></th></tr>

<span py:if="category.applications" py:for="application in category.applications">

<tr class="application"><th><h3><a href="/application/${application.id}/">${application.name}</a></h3></th></tr>

<tr class="deployment nested-${deployment.status()}" py:for="deployment in application.deployments"><th><a href="/deployment/${deployment.id}/">${deployment.name}</a></th></tr>

</span>
</span>

</table>

</div>

<form action="/add_category" method="post">
<p>Add A New Category: <input type="text" name="name" /> <input
type="submit" value="Add" /></p>
</form>

</body>
</html>
