<html>
<head><title>My Book Collection</title></head>
<body>
  <h1>My Book Collection</h1>
  <a href="/">Show all</a>
  <table border="1">
    <tr><th>Tag</th><th>Title</th><th>Description</th><th>Rating</th><th>&nbsp;</th></tr>
    %for bk in books:
      <tr>
        <td><a href="?tagid={{bk.tag.id}}">{{bk.tag.name}}</a></td>
        <td>{{bk.title}}</td><td>{{bk.description}}</td><td style="text-align:center">{{bk.rating}}</td>
        <td><a href="/delete/{{bk.id}}">Del</a></td>
      </tr>
    %end
  </table>
  <hr>
  <h2>Register book</h2>
  <form method="POST">
    <table>
    <tr><th>Tag</th><th>Title</th><th>Description</th><th>Rating</th></tr>
    <tr>
      <td><input type="text" id="tag" name="tag" size="10" value="" />
      <td><input type="text" id="title" name="title" size="20" value="" />
      <td><input type="text" id="desc" name="desc" size="50" value="" />
      <td>
        <select id="rating" name="rating">
          <option value="5">5</option>
          <option value="4">4</option>
          <option value="3">3</option>
          <option value="2">2</option>
          <option value="1">1</option>
        </select>
      </td>
      <td><input type="submit" value="Register" /></td>
    </tr>
    </table>
  </form>
</body>
</html>

