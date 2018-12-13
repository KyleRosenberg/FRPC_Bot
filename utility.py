def similarityDistance(s, t):
  # Determine the "optimal" string-alignment distance between s and t
  if (not s or not t):
    return 99;

  m = len(s);
  n = len(t);

  ''' For all i and j, d[i][j] holds the string-alignment distance
    between the first i characters of s and the first j characters of t.
    Note that the array has (m+1)x(n+1) values.
   '''
  d = [0]*(m+1)
  for i in range(m+1):
    d[i] = [0]*(n+1)
    d[i][0] = i;

  for j in range(n+1):
    d[0][j] = j;


  # Determine substring distances
  cost = 0;
  for j in range(1, n+1):
    for i in range(1, m+1):
      cost = 0 if (s[i-1] == t[j-1]) else 1;   # Subtract one to start at strings' index zero instead of index one
      d[i][j] = min(d[i][j-1] + 1,                  # insertion
                         min(d[i-1][j] + 1,         # deletion
                                  d[i-1][j-1] + cost));  # substitution

      #if(i > 1 and j > 1 and s[i-1] == t[j-2] and s[i-2] == t[j-1]):
        #d[i][j] = min(d[i][j], d[i-2][j-2] + cost); # transposition

  # Return the strings' distance
  return d[m][n];
