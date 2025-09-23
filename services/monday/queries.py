# Placeholder for Monday GraphQL queries
GET_ITEMS_QUERY = '''
query getItems($boardId: Int!) {
  boards(ids: [$boardId]) {
    items {
      id
      name
      column_values {
        id
        text
      }
    }
  }
}
'''

GET_BOARD_STRUCTURE_QUERY = '''
query getBoardStructure($boardId: ID!) {
    boards(ids: [$boardId]) {
        groups {
            id
            title
        }
        columns {
            id
            title
        }
    }
}
'''

GET_ALL_ITEMS_QUERY = '''
query getAllItems($boardId: [ID!]!, $groupId: [String]!, $columnIds: [String!]) {
    boards(ids: $boardId) {
        groups(ids: $groupId) {
            items_page(limit: 500) {
                items {
                    id
                    name
                    column_values(ids: $columnIds) {
                        id
                        text
                    }
                }
            }
        }
    }
}
'''
