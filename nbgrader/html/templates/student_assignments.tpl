{%- extends 'gradebook.tpl' -%}

{%- block breadcrumb -%}
<li><a href="/students">Students</a></li>
<li class="active">{{ student.id }}</li>
{%- endblock -%}

{%- block body -%}
<div class="panel-body">
  The following table lists the assignments turned in by {{ student.last_name }}, {{ student.first_name }}. Click on a notebook
  name to see the scores for individual notebooks.
</div>
{%- endblock -%}

{%- block table -%}
<thead>
  <tr>
    <th>Assignment ID</th>
    <th class="center">Overall Score</th>
    <th class="center">Code Score</th>
    <th class="center">Written Score</th>
  </tr>
</thead>
<tbody>
  {%- for assignment in assignments -%}
  <tr>
    <td><a href="/students/{{ student.id }}/{{ assignment.name }}">{{ assignment.name }}</a></td>
    <td class="center">
      {{ assignment.score | float | round(2) }} / {{ assignment.max_score | float | round(2) }}
    </td>
    <td class="center">
      {{ assignment.code_score | float | round(2) }} / {{ assignment.max_code_score | float | round(2) }}
    </td>
    <td class="center">
      {{ assignment.written_score | float | round(2) }} / {{ assignment.max_written_score | float | round(2) }}
    </td>
  </tr>
  {%- endfor -%}
</tbody>
{%- endblock -%}